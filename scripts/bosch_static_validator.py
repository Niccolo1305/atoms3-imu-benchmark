#!/usr/bin/env python3
"""
Bosch BMI270 + BMM150 static log validator.

The script follows the lab-notebook blueprint used for long static runs:
CSV ingestion, thermal plateau isolation, offset checks, Welch PSD,
overlapping Allan deviation, thermal drift fitting, and a diagnostic dashboard.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import find_peaks, welch


HEADER_UNIT_RE = re.compile(r"\s*\([^)]*\)\s*$")

ACCEL_Z_LIMIT_G = 0.02
GYRO_ZRO_LIMIT_DPS = 0.5
MAG_ZERO_B_LIMIT_UT = 40.0
GYRO_TCO_LIMIT_DPS_PER_C = 0.02
SHAPIRO_ALPHA = 0.05
SHAPIRO_MAX_N = 5000
ALLAN_LOW_CONFIDENCE_N = 10
SNR_EXCELLENT_DB = 40.0
SNR_GOOD_DB = 25.0
SNR_FAIR_DB = 10.0

AXES = ("x", "y", "z")
BMI_ACCEL_COLUMNS = {axis: f"bmi_acc_{axis}_g" for axis in AXES}
BMI_GYRO_COLUMNS = {axis: f"bmi_gyr_{axis}_dps" for axis in AXES}
BMM_MAG_COLUMNS = {axis: f"bmm_mag_{axis}_ut" for axis in AXES}


@dataclass(frozen=True)
class Plateau:
    start_idx: int
    end_idx: int
    start_s: float
    end_s: float
    temp_mean_c: float
    median_abs_slope_c_min: float
    found: bool
    note: str = ""


@dataclass(frozen=True)
class AllanResult:
    taus: np.ndarray
    adev: np.ndarray
    ns: np.ndarray
    ci95_low: np.ndarray
    ci95_high: np.ndarray
    bias_instability: float
    bias_tau_s: float
    random_walk_density: float
    random_walk_tau_s: float
    source: str


@dataclass(frozen=True)
class PsdResult:
    freq_hz: np.ndarray
    density: np.ndarray
    noise_floor: float
    spikes_hz: list[float]
    slope_loglog: float
    spectral_flatness: float
    strong_peak_count: int
    whiteness_rating: str


@dataclass(frozen=True)
class TcoResult:
    slope: float
    intercept: float
    linear_r2: float
    fit_degree: int
    fit_coeffs: np.ndarray
    temp_span_c: float
    sample_count: int


@dataclass(frozen=True)
class ThermalHysteresis:
    temp_overlap_c: float
    bin_count: int
    mean_abs_delta: float
    max_abs_delta: float
    status: str
    note: str = ""


@dataclass(frozen=True)
class TimingQuality:
    sample_count: int
    duration_s: float
    fs_median_hz: float
    fs_mean_hz: float
    dt_median_s: float
    dt_mean_s: float
    dt_std_s: float
    dt_min_s: float
    dt_max_s: float
    jitter_rms_us: float
    jitter_p95_us: float
    timing_outlier_count: int
    estimated_dropped_samples: int
    duplicate_time_count: int
    fifo_overrun_count: int | None
    fifo_backlog_max: float | None
    imu_sample_fresh_rate: float | None
    mag_sample_fresh_rate: float | None
    status: str
    note: str


def normalize_column(name: object) -> str:
    normalized = HEADER_UNIT_RE.sub("", str(name)).strip().lower()
    normalized = normalized.replace(" ", "_").replace("-", "_")
    normalized = normalized.replace("µ", "u").replace("μ", "u")
    normalized = normalized.replace("°", "deg")
    return normalized


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, comment="#", encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return pd.read_csv(path, comment="#")


def first_present(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    available = set(columns)
    for candidate in candidates:
        if candidate in available:
            return candidate
    return None


def canonicalize_log(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    df.columns = [normalize_column(col) for col in df.columns]

    aliases = {
        "bmi_acc_x_g": ("bmi_acc_x_g", "bmi_post_lpf20_prepipe_acc_x_g", "bmi_post_lpf20_prepipe_ax_g"),
        "bmi_acc_y_g": ("bmi_acc_y_g", "bmi_post_lpf20_prepipe_acc_y_g", "bmi_post_lpf20_prepipe_ay_g"),
        "bmi_acc_z_g": ("bmi_acc_z_g", "bmi_post_lpf20_prepipe_acc_z_g", "bmi_post_lpf20_prepipe_az_g"),
        "bmi_gyr_x_dps": ("bmi_gyr_x_dps", "bmi_post_lpf20_prepipe_gyr_x_dps", "bmi_post_lpf20_prepipe_gx_dps"),
        "bmi_gyr_y_dps": ("bmi_gyr_y_dps", "bmi_post_lpf20_prepipe_gyr_y_dps", "bmi_post_lpf20_prepipe_gy_dps"),
        "bmi_gyr_z_dps": ("bmi_gyr_z_dps", "bmi_post_lpf20_prepipe_gyr_z_dps", "bmi_post_lpf20_prepipe_gz_dps"),
        "bmm_mag_x_ut": ("bmm_mag_x_ut", "bmm_ut_x", "bmm_x_ut", "mag_x_ut"),
        "bmm_mag_y_ut": ("bmm_mag_y_ut", "bmm_ut_y", "bmm_y_ut", "mag_y_ut"),
        "bmm_mag_z_ut": ("bmm_mag_z_ut", "bmm_ut_z", "bmm_z_ut", "mag_z_ut"),
    }
    for target, candidates in aliases.items():
        source = first_present(df.columns, candidates)
        if source is not None and target not in df.columns:
            df[target] = df[source]

    time_us_col = first_present(df.columns, ("t_us", "time_us"))
    time_ms_col = first_present(df.columns, ("t_ms", "time_ms"))
    if time_us_col is not None:
        df["t_us"] = pd.to_numeric(df[time_us_col], errors="coerce")
        t0 = df["t_us"].dropna().iloc[0]
        df["time_s"] = (df["t_us"] - t0) / 1_000_000.0
    elif time_ms_col is not None:
        df["t_ms"] = pd.to_numeric(df[time_ms_col], errors="coerce")
        t0 = df["t_ms"].dropna().iloc[0]
        df["time_s"] = (df["t_ms"] - t0) / 1_000.0
    else:
        raise ValueError("Missing time column: expected t_us or t_ms")

    target_columns = [
        "time_s",
        "temp_c",
        "bmi_acc_x_g",
        "bmi_acc_y_g",
        "bmi_acc_z_g",
        "bmi_gyr_x_dps",
        "bmi_gyr_y_dps",
        "bmi_gyr_z_dps",
        "bmm_mag_x_ut",
        "bmm_mag_y_ut",
        "bmm_mag_z_ut",
    ]
    missing = [col for col in target_columns if col not in df.columns]
    if missing:
        raise ValueError("Missing required Bosch columns: " + ", ".join(missing))

    numeric_columns = set(target_columns)
    for optional in (
        "mag_valid",
        "mag_overflow",
        "mag_sample_fresh",
        "imu_sample_fresh",
        "fifo_frames_drained",
        "fifo_backlog",
        "fifo_overrun",
    ):
        if optional in df.columns:
            numeric_columns.add(optional)
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    original_len = len(df)
    df = (
        df.dropna(subset=["time_s"])
        .sort_values("time_s")
    )
    duplicate_time_count = int(df.duplicated(subset=["time_s"]).sum())
    df = df.drop_duplicates(subset=["time_s"], keep="first").reset_index(drop=True)
    df.attrs["dropped_invalid_time_count"] = original_len - len(df) - duplicate_time_count
    df.attrs["duplicate_time_count"] = duplicate_time_count

    if "mag_valid" in df.columns:
        invalid_mag = df["mag_valid"] != 1
        for col in ("bmm_mag_x_ut", "bmm_mag_y_ut", "bmm_mag_z_ut"):
            df.loc[invalid_mag, col] = np.nan
    if "mag_overflow" in df.columns:
        overflow_mag = df["mag_overflow"] != 0
        for col in ("bmm_mag_x_ut", "bmm_mag_y_ut", "bmm_mag_z_ut"):
            df.loc[overflow_mag, col] = np.nan

    return df


def estimate_sampling_rate(time_s: pd.Series) -> float:
    diffs = np.diff(time_s.to_numpy(dtype=float))
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if len(diffs) == 0:
        raise ValueError("Cannot estimate sampling rate: non-increasing timestamps")
    return float(1.0 / np.median(diffs))


def optional_nonzero_count(df: pd.DataFrame, column: str) -> int | None:
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce")
    return int(np.sum(values.fillna(0).to_numpy(dtype=float) != 0.0))


def optional_max(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return None
    return float(np.max(values))


def optional_true_rate(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    values = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return None
    return float(np.mean(values != 0.0))


def compute_timing_quality(df: pd.DataFrame, fs: float) -> TimingQuality:
    time_s = df["time_s"].to_numpy(dtype=float)
    diffs = np.diff(time_s)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if len(diffs) == 0:
        return TimingQuality(
            sample_count=len(df),
            duration_s=0.0,
            fs_median_hz=fs,
            fs_mean_hz=math.nan,
            dt_median_s=math.nan,
            dt_mean_s=math.nan,
            dt_std_s=math.nan,
            dt_min_s=math.nan,
            dt_max_s=math.nan,
            jitter_rms_us=math.nan,
            jitter_p95_us=math.nan,
            timing_outlier_count=0,
            estimated_dropped_samples=0,
            duplicate_time_count=int(df.attrs.get("duplicate_time_count", 0)),
            fifo_overrun_count=optional_nonzero_count(df, "fifo_overrun"),
            fifo_backlog_max=optional_max(df, "fifo_backlog"),
            imu_sample_fresh_rate=optional_true_rate(df, "imu_sample_fresh"),
            mag_sample_fresh_rate=optional_true_rate(df, "mag_sample_fresh"),
            status="FAIL",
            note="not enough timestamp intervals",
        )

    dt_median_s = float(np.median(diffs))
    dt_mean_s = float(np.mean(diffs))
    dt_std_s = float(np.std(diffs))
    fs_mean_hz = float(1.0 / dt_mean_s) if dt_mean_s > 0 else math.nan
    jitter = diffs - dt_median_s
    abs_jitter = np.abs(jitter)
    jitter_rms_us = float(math.sqrt(np.mean(jitter * jitter)) * 1_000_000.0)
    jitter_p95_us = float(np.percentile(abs_jitter, 95.0) * 1_000_000.0)
    outlier_threshold_s = max(0.10 * dt_median_s, 0.001)
    timing_outlier_count = int(np.sum(abs_jitter > outlier_threshold_s))
    dropped_samples = int(
        np.sum(np.maximum(0, np.round(diffs / dt_median_s).astype(int) - 1)[diffs > 1.5 * dt_median_s])
    )
    duplicate_time_count = int(df.attrs.get("duplicate_time_count", 0))
    fifo_overrun_count = optional_nonzero_count(df, "fifo_overrun")
    fifo_backlog_max = optional_max(df, "fifo_backlog")
    imu_sample_fresh_rate = optional_true_rate(df, "imu_sample_fresh")
    mag_sample_fresh_rate = optional_true_rate(df, "mag_sample_fresh")

    hard_fail = duplicate_time_count > 0 or dropped_samples > 0 or (fifo_overrun_count or 0) > 0
    warn = timing_outlier_count > max(1, int(0.01 * len(diffs))) or jitter_p95_us > dt_median_s * 100_000.0
    status = "FAIL" if hard_fail else ("WARN" if warn else "PASS")
    notes: list[str] = []
    if duplicate_time_count:
        notes.append(f"{duplicate_time_count} duplicate timestamps removed")
    if dropped_samples:
        notes.append(f"{dropped_samples} estimated dropped samples")
    if fifo_overrun_count:
        notes.append(f"{fifo_overrun_count} FIFO overrun rows")
    if warn and not hard_fail:
        notes.append("timestamp jitter/outlier warning")

    return TimingQuality(
        sample_count=len(df),
        duration_s=float(time_s[-1] - time_s[0]) if len(time_s) else 0.0,
        fs_median_hz=fs,
        fs_mean_hz=fs_mean_hz,
        dt_median_s=dt_median_s,
        dt_mean_s=dt_mean_s,
        dt_std_s=dt_std_s,
        dt_min_s=float(np.min(diffs)),
        dt_max_s=float(np.max(diffs)),
        jitter_rms_us=jitter_rms_us,
        jitter_p95_us=jitter_p95_us,
        timing_outlier_count=timing_outlier_count,
        estimated_dropped_samples=dropped_samples,
        duplicate_time_count=duplicate_time_count,
        fifo_overrun_count=fifo_overrun_count,
        fifo_backlog_max=fifo_backlog_max,
        imu_sample_fresh_rate=imu_sample_fresh_rate,
        mag_sample_fresh_rate=mag_sample_fresh_rate,
        status=status,
        note="; ".join(notes) if notes else "nominal",
    )


def contiguous_segments(mask: np.ndarray) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    in_segment = False
    start = 0
    for idx, value in enumerate(mask):
        if value and not in_segment:
            start = idx
            in_segment = True
        elif not value and in_segment:
            segments.append((start, idx - 1))
            in_segment = False
    if in_segment:
        segments.append((start, len(mask) - 1))
    return segments


def find_temperature_plateaus(
    df: pd.DataFrame,
    fs: float,
    max_slope_c_min: float = 0.05,
    smooth_window_s: float = 60.0,
    min_duration_s: float = 300.0,
) -> Plateau:
    time_s = df["time_s"].to_numpy(dtype=float)
    temp = df["temp_c"].interpolate(limit_direction="both").to_numpy(dtype=float)
    if len(time_s) < 3:
        raise ValueError("Not enough samples to detect a thermal plateau")

    window = max(3, int(round(smooth_window_s * fs)))
    temp_smooth = (
        pd.Series(temp)
        .rolling(window=window, center=True, min_periods=max(3, window // 5))
        .mean()
        .bfill()
        .ffill()
        .to_numpy(dtype=float)
    )

    slope_c_min = np.gradient(temp_smooth) * fs * 60.0
    slope_abs = np.abs(slope_c_min)
    slope_abs_smooth = (
        pd.Series(slope_abs)
        .rolling(window=window, center=True, min_periods=1)
        .mean()
        .to_numpy(dtype=float)
    )

    stable = slope_abs_smooth <= max_slope_c_min
    segments = contiguous_segments(stable)
    total_duration_s = float(time_s[-1] - time_s[0])
    effective_min_duration_s = min(min_duration_s, max(30.0, total_duration_s * 0.25))

    candidates = [
        (start, end)
        for start, end in segments
        if (time_s[end] - time_s[start]) >= effective_min_duration_s
    ]
    found = True
    note = ""
    if not candidates:
        candidates = segments
        found = False
        note = f"no segment reached {effective_min_duration_s:.0f}s at ±{max_slope_c_min:.2f} °C/min"

    if not candidates:
        start = len(df) // 3
        end = len(df) - 1
        found = False
        note = "no stable slope samples found; using final two thirds"
    else:
        start, end = sorted(
            candidates,
            key=lambda item: (
                -(time_s[item[1]] - time_s[item[0]]),
                float(np.nanmedian(slope_abs_smooth[item[0] : item[1] + 1])),
            ),
        )[0]

    return Plateau(
        start_idx=int(start),
        end_idx=int(end),
        start_s=float(time_s[start]),
        end_s=float(time_s[end]),
        temp_mean_c=float(np.nanmean(temp[start : end + 1])),
        median_abs_slope_c_min=float(np.nanmedian(slope_abs_smooth[start : end + 1])),
        found=found,
        note=note,
    )


def finite_values(series: pd.Series) -> np.ndarray:
    values = series.to_numpy(dtype=float)
    return values[np.isfinite(values)]


def pass_fail(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def shapiro_p_value(values: np.ndarray) -> float:
    values = values[np.isfinite(values)]
    if len(values) < 3:
        return math.nan
    if len(values) > SHAPIRO_MAX_N:
        indices = np.linspace(0, len(values) - 1, SHAPIRO_MAX_N).astype(int)
        values = values[indices]
    return float(stats.shapiro(values).pvalue)


def compute_psd(values: np.ndarray, fs: float, nperseg: int = 1024) -> PsdResult:
    values = values[np.isfinite(values)]
    if len(values) < 8:
        return PsdResult(np.array([]), np.array([]), math.nan, [], math.nan, math.nan, 0, "NA")
    segment_len = min(nperseg, len(values))
    freq_hz, pxx = welch(
        values - np.nanmean(values),
        fs=fs,
        nperseg=segment_len,
        detrend="constant",
        scaling="density",
    )
    density = np.sqrt(np.maximum(pxx, 0.0))
    band = (freq_hz > max(0.05, fs / max(len(values), 1))) & (freq_hz < fs * 0.45)
    if not np.any(band):
        return PsdResult(freq_hz, density, math.nan, [], math.nan, math.nan, 0, "NA")
    floor = float(np.nanmedian(density[band]))
    if not math.isfinite(floor) or floor <= 0:
        return PsdResult(freq_hz, density, floor, [], math.nan, math.nan, 0, "NA")
    peak_idx, props = find_peaks(density[band], prominence=floor * 5.0)
    band_freq = freq_hz[band]
    band_density = density[band]
    ranked = sorted(peak_idx, key=lambda idx: band_density[idx] / floor, reverse=True)
    spikes = [float(band_freq[idx]) for idx in ranked[:5] if band_density[idx] / floor >= 10.0]
    strong_peak_count = int(np.sum(band_density[peak_idx] / floor >= 10.0)) if len(peak_idx) else 0

    whiteness_band = (freq_hz >= max(0.2, fs / max(len(values), 1) * 2.0)) & (freq_hz <= fs * 0.40)
    slope_loglog = math.nan
    spectral_flatness = math.nan
    if np.sum(whiteness_band) >= 8:
        x = np.log10(freq_hz[whiteness_band])
        y = np.log10(np.maximum(pxx[whiteness_band], np.finfo(float).tiny))
        if len(np.unique(x)) >= 2:
            slope_loglog = float(np.polyfit(x, y, 1)[0])
        power_band = np.maximum(pxx[whiteness_band], np.finfo(float).tiny)
        spectral_flatness = float(np.exp(np.mean(np.log(power_band))) / np.mean(power_band))

    return PsdResult(
        freq_hz,
        density,
        floor,
        spikes,
        slope_loglog,
        spectral_flatness,
        strong_peak_count,
        psd_whiteness_rating(spectral_flatness, slope_loglog, strong_peak_count),
    )


def generate_taus(duration_s: float, fs: float, count: int = 50) -> np.ndarray:
    min_tau = max(0.1, 1.0 / fs)
    max_tau = duration_s / 3.0
    if max_tau <= min_tau:
        return np.array([])
    raw = np.logspace(np.log10(min_tau), np.log10(max_tau), count)
    sample_counts = np.unique(np.maximum(1, np.round(raw * fs).astype(int)))
    return sample_counts / fs


def oadev_numpy(values: np.ndarray, fs: float, taus: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = values[np.isfinite(values)]
    n = len(values)
    if n < 8:
        return np.array([]), np.array([]), np.array([])

    cumsum = np.concatenate(([0.0], np.cumsum(values)))
    out_taus: list[float] = []
    out_adev: list[float] = []
    out_ns: list[int] = []
    for tau in taus:
        m = max(1, int(round(tau * fs)))
        if 2 * m > n:
            continue
        second_diff = cumsum[2 * m :] - 2.0 * cumsum[m:-m] + cumsum[: -2 * m]
        if len(second_diff) == 0:
            continue
        avar = float(np.sum(second_diff * second_diff)) / (2.0 * m * m * len(second_diff))
        out_taus.append(m / fs)
        out_adev.append(math.sqrt(max(avar, 0.0)))
        out_ns.append(len(second_diff))
    return np.asarray(out_taus), np.asarray(out_adev), np.asarray(out_ns, dtype=float)


def allan_ci95(adev: np.ndarray, ns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    low = np.full_like(adev, np.nan, dtype=float)
    high = np.full_like(adev, np.nan, dtype=float)
    valid = np.isfinite(adev) & np.isfinite(ns) & (adev > 0) & (ns > 1)
    if not np.any(valid):
        return low, high
    dof = ns[valid]
    low[valid] = adev[valid] * np.sqrt(dof / stats.chi2.ppf(0.975, dof))
    high[valid] = adev[valid] * np.sqrt(dof / stats.chi2.ppf(0.025, dof))
    return low, high


def random_walk_from_tau_one(tau_out: np.ndarray, adev: np.ndarray) -> tuple[float, float]:
    target_tau_s = 1.0
    if len(tau_out) == 0:
        return math.nan, math.nan

    if float(np.min(tau_out)) <= target_tau_s <= float(np.max(tau_out)):
        adev_at_tau = float(
            np.exp(np.interp(np.log(target_tau_s), np.log(tau_out), np.log(adev)))
        )
        tau_ref_s = target_tau_s
    else:
        idx = int(np.argmin(np.abs(np.log(tau_out) - math.log(target_tau_s))))
        adev_at_tau = float(adev[idx])
        tau_ref_s = float(tau_out[idx])

    return float(adev_at_tau * math.sqrt(2.0 * tau_ref_s)), tau_ref_s


def compute_allan(values: np.ndarray, fs: float, duration_s: float) -> AllanResult:
    taus = generate_taus(duration_s, fs)
    if len(taus) == 0:
        empty = np.array([])
        return AllanResult(empty, empty, empty, empty, empty, math.nan, math.nan, math.nan, math.nan, "none")

    source = "numpy"
    try:
        import allantools  # type: ignore

        tau_out, adev, _, ns = allantools.oadev(values, rate=fs, data_type="freq", taus=taus)
        tau_out = np.asarray(tau_out, dtype=float)
        adev = np.asarray(adev, dtype=float)
        ns = np.asarray(ns, dtype=float)
        source = "allantools"
    except Exception:
        tau_out, adev, ns = oadev_numpy(values, fs, taus)

    valid = np.isfinite(tau_out) & np.isfinite(adev) & (tau_out > 0) & (adev > 0)
    tau_out = tau_out[valid]
    adev = adev[valid]
    ns = ns[valid] if len(ns) == len(valid) else np.full_like(adev, np.nan, dtype=float)
    ci95_low, ci95_high = allan_ci95(adev, ns)
    if len(tau_out) == 0:
        return AllanResult(tau_out, adev, ns, ci95_low, ci95_high, math.nan, math.nan, math.nan, math.nan, source)

    bias_idx = int(np.argmin(adev))
    random_walk_density, random_walk_tau_s = random_walk_from_tau_one(tau_out, adev)
    return AllanResult(
        tau_out,
        adev,
        ns,
        ci95_low,
        ci95_high,
        bias_instability=float(adev[bias_idx]),
        bias_tau_s=float(tau_out[bias_idx]),
        random_walk_density=random_walk_density,
        random_walk_tau_s=random_walk_tau_s,
        source=source,
    )


def r_squared(y: np.ndarray, predicted: np.ndarray) -> float:
    residual = y - predicted
    ss_res = float(np.sum(residual * residual))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0


def fit_tco(df: pd.DataFrame, sensor_col: str, fs: float, temp_col: str = "temp_c") -> TcoResult:
    fit_df = df[[temp_col, sensor_col]].dropna()
    if "time_s" in df.columns:
        fit_df = df[["time_s", temp_col, sensor_col]].dropna().sort_values("time_s")
    if len(fit_df) < 3:
        coeffs = np.array([math.nan, math.nan])
        return TcoResult(math.nan, math.nan, math.nan, 1, coeffs, math.nan, 0)

    window = max(3, int(round(30.0 * fs)))
    window = min(window, max(3, len(fit_df) // 4))
    temp_smooth = (
        fit_df[temp_col]
        .rolling(window=window, center=True, min_periods=3)
        .mean()
        .bfill()
        .ffill()
    )
    sensor_smooth = (
        fit_df[sensor_col]
        .rolling(window=window, center=True, min_periods=3)
        .mean()
        .bfill()
        .ffill()
    )

    max_temp_idx = int(np.nanargmax(temp_smooth.to_numpy(dtype=float)))
    fit_df = fit_df.iloc[: max_temp_idx + 1].copy()
    temp_smooth = temp_smooth.iloc[: max_temp_idx + 1]
    sensor_smooth = sensor_smooth.iloc[: max_temp_idx + 1]

    x = temp_smooth.to_numpy(dtype=float)
    y = sensor_smooth.to_numpy(dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    if len(x) < 3 or len(np.unique(x)) < 2:
        coeffs = np.array([math.nan, math.nan])
        return TcoResult(math.nan, math.nan, math.nan, 1, coeffs, math.nan, len(x))

    linear_coeffs = np.polyfit(x, y, 1)
    linear_pred = np.polyval(linear_coeffs, x)
    linear_r2 = r_squared(y, linear_pred)

    return TcoResult(
        slope=float(linear_coeffs[0]),
        intercept=float(linear_coeffs[1]),
        linear_r2=float(linear_r2),
        fit_degree=1,
        fit_coeffs=np.asarray(linear_coeffs, dtype=float),
        temp_span_c=float(np.max(x) - np.min(x)),
        sample_count=int(len(x)),
    )


def compute_thermal_hysteresis(
    df: pd.DataFrame,
    sensor_col: str,
    fs: float,
    temp_col: str = "temp_c",
    slope_threshold_c_min: float = 0.02,
) -> ThermalHysteresis:
    fit_df = df[["time_s", temp_col, sensor_col]].dropna().sort_values("time_s")
    if len(fit_df) < max(20, int(10 * fs)):
        return ThermalHysteresis(math.nan, 0, math.nan, math.nan, "NA", "not enough samples")

    window = max(3, int(round(30.0 * fs)))
    window = min(window, max(3, len(fit_df) // 4))
    temp_smooth = (
        fit_df[temp_col]
        .rolling(window=window, center=True, min_periods=3)
        .mean()
        .bfill()
        .ffill()
        .to_numpy(dtype=float)
    )
    sensor_smooth = (
        fit_df[sensor_col]
        .rolling(window=window, center=True, min_periods=3)
        .mean()
        .bfill()
        .ffill()
        .to_numpy(dtype=float)
    )
    slope_c_min = np.gradient(temp_smooth) * fs * 60.0
    warming = slope_c_min > slope_threshold_c_min
    cooling = slope_c_min < -slope_threshold_c_min
    min_phase_samples = max(10, int(30.0 * fs))
    if int(np.sum(warming)) < min_phase_samples or int(np.sum(cooling)) < min_phase_samples:
        return ThermalHysteresis(math.nan, 0, math.nan, math.nan, "NA", "warming/cooling phases not both present")

    warm_temp = temp_smooth[warming]
    cool_temp = temp_smooth[cooling]
    low = max(float(np.min(warm_temp)), float(np.min(cool_temp)))
    high = min(float(np.max(warm_temp)), float(np.max(cool_temp)))
    overlap = high - low
    if overlap <= 0.2:
        return ThermalHysteresis(overlap, 0, math.nan, math.nan, "NA", "temperature overlap too small")

    bin_count = int(min(20, max(3, math.floor(overlap / 0.2))))
    bins = np.linspace(low, high, bin_count + 1)
    deltas: list[float] = []
    for start, end in zip(bins[:-1], bins[1:]):
        warm_bin = warming & (temp_smooth >= start) & (temp_smooth < end)
        cool_bin = cooling & (temp_smooth >= start) & (temp_smooth < end)
        if np.sum(warm_bin) < 3 or np.sum(cool_bin) < 3:
            continue
        deltas.append(float(np.nanmean(sensor_smooth[cool_bin]) - np.nanmean(sensor_smooth[warm_bin])))

    if not deltas:
        return ThermalHysteresis(overlap, 0, math.nan, math.nan, "NA", "no populated overlap bins")

    abs_deltas = np.abs(np.asarray(deltas, dtype=float))
    status = "PASS"
    return ThermalHysteresis(
        temp_overlap_c=float(overlap),
        bin_count=len(deltas),
        mean_abs_delta=float(np.mean(abs_deltas)),
        max_abs_delta=float(np.max(abs_deltas)),
        status=status,
        note="cooling minus warming at matched temperature bins",
    )


def nearest_index(values: np.ndarray, target: float) -> int | None:
    valid = np.isfinite(values)
    if not np.any(valid) or not math.isfinite(target):
        return None
    valid_indices = np.flatnonzero(valid)
    idx = valid_indices[int(np.argmin(np.abs(values[valid] - target)))]
    return int(idx)


def ci95_at_tau(allan: AllanResult, tau_s: float) -> dict[str, float | None]:
    idx = nearest_index(allan.taus, tau_s)
    if idx is None:
        return {"tau_s": None, "low": None, "high": None, "n": None}
    return {
        "tau_s": json_float(allan.taus[idx]),
        "low": json_float(allan.ci95_low[idx]),
        "high": json_float(allan.ci95_high[idx]),
        "n": json_float(allan.ns[idx]),
    }


def json_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def snr_rating(snr_db: float) -> str:
    if not math.isfinite(snr_db):
        return "NA"
    if snr_db >= SNR_EXCELLENT_DB:
        return "EXCELLENT"
    if snr_db >= SNR_GOOD_DB:
        return "GOOD"
    if snr_db >= SNR_FAIR_DB:
        return "FAIR"
    return "POOR"


def snr_summary(mean_value: float, std_value: float) -> dict[str, object]:
    if not math.isfinite(mean_value) or not math.isfinite(std_value) or std_value <= 0:
        return {
            "linear": None,
            "db": None,
            "rating": "NA",
            "definition": "abs(mean_plateau)/std_plateau",
        }
    linear = abs(mean_value) / std_value
    snr_db = 20.0 * math.log10(linear) if linear > 0 else math.nan
    return {
        "linear": json_float(linear),
        "db": json_float(snr_db),
        "rating": snr_rating(snr_db),
        "definition": "abs(mean_plateau)/std_plateau",
    }


def psd_whiteness_rating(flatness: float, slope_loglog: float, strong_peak_count: int) -> str:
    if not math.isfinite(flatness) or not math.isfinite(slope_loglog):
        return "NA"
    if strong_peak_count == 0 and abs(slope_loglog) <= 0.15 and flatness >= 0.55:
        return "WHITE"
    if strong_peak_count <= 2 and abs(slope_loglog) <= 0.35 and flatness >= 0.30:
        return "FAIR"
    return "COLORED"


def psd_summary(psd: PsdResult, scale: float = 1.0) -> dict[str, object]:
    return {
        "noise_floor": json_float(psd.noise_floor * scale),
        "spikes_hz": [float(freq) for freq in psd.spikes_hz],
        "frequency_bin_count": int(len(psd.freq_hz)),
        "slope_loglog": json_float(psd.slope_loglog),
        "spectral_flatness": json_float(psd.spectral_flatness),
        "strong_peak_count": int(psd.strong_peak_count),
        "whiteness_rating": psd.whiteness_rating,
    }


def allan_summary(allan: AllanResult) -> dict[str, object]:
    if len(allan.taus) == 0:
        return {
            "source": allan.source,
            "tau_count": 0,
            "bias_instability": None,
            "bias_tau_s": None,
            "random_walk_density": None,
            "random_walk_tau_s": None,
            "min_equivalent_count": None,
            "low_confidence_tau_count": 0,
        }
    finite_ns = allan.ns[np.isfinite(allan.ns)]
    return {
        "source": allan.source,
        "tau_count": int(len(allan.taus)),
        "tau_min_s": json_float(np.min(allan.taus)),
        "tau_max_s": json_float(np.max(allan.taus)),
        "bias_instability": json_float(allan.bias_instability),
        "bias_tau_s": json_float(allan.bias_tau_s),
        "bias_instability_ci95": ci95_at_tau(allan, allan.bias_tau_s),
        "random_walk_density": json_float(allan.random_walk_density),
        "random_walk_tau_s": json_float(allan.random_walk_tau_s),
        "random_walk_ci95": ci95_at_tau(allan, allan.random_walk_tau_s),
        "min_equivalent_count": json_float(np.min(finite_ns)) if len(finite_ns) else None,
        "low_confidence_tau_count": int(np.sum(finite_ns < ALLAN_LOW_CONFIDENCE_N)) if len(finite_ns) else 0,
    }


def rolling_mean_summary(values: np.ndarray, window_samples: int) -> dict[str, float | None]:
    if len(values) < 3:
        return {
            "window_samples": int(window_samples),
            "sample_count": int(len(values)),
            "std": None,
            "p2p": None,
            "max_abs": None,
        }
    min_periods = max(3, min(window_samples, max(3, window_samples // 3)))
    rolled = (
        pd.Series(values)
        .rolling(window=max(1, window_samples), center=False, min_periods=min_periods)
        .mean()
        .to_numpy(dtype=float)
    )
    rolled = rolled[np.isfinite(rolled)]
    if len(rolled) == 0:
        return {
            "window_samples": int(window_samples),
            "sample_count": 0,
            "std": None,
            "p2p": None,
            "max_abs": None,
        }
    return {
        "window_samples": int(window_samples),
        "sample_count": int(len(rolled)),
        "std": json_float(np.std(rolled)),
        "p2p": json_float(np.max(rolled) - np.min(rolled)),
        "max_abs": json_float(np.max(np.abs(rolled))),
    }


def gyro_residual_stability(
    df_plateau: pd.DataFrame,
    column: str,
    fs: float,
    mean_value: float,
) -> dict[str, object]:
    fit_df = df_plateau[["time_s", column]].dropna().sort_values("time_s")
    empty_roll60 = rolling_mean_summary(np.array([]), max(1, int(round(60.0 * fs))))
    empty_roll300 = rolling_mean_summary(np.array([]), max(1, int(round(300.0 * fs))))
    if len(fit_df) < 3 or not math.isfinite(mean_value):
        return {
            "mean_removed": None,
            "residual_std_dps": None,
            "residual_slope_dps_per_h": None,
            "angle_final_deg": None,
            "angle_p2p_deg": None,
            "roll60": empty_roll60,
            "roll300": empty_roll300,
        }

    time_s = fit_df["time_s"].to_numpy(dtype=float)
    values = fit_df[column].to_numpy(dtype=float)
    residual = values - mean_value
    centered_time_s = time_s - time_s[0]
    slope_dps_per_h = math.nan
    if len(np.unique(centered_time_s)) >= 2:
        slope_dps_per_h = float(np.polyfit(centered_time_s, residual, 1)[0] * 3600.0)

    dt = np.diff(time_s)
    angle = np.zeros(len(residual), dtype=float)
    if len(dt) > 0:
        angle[1:] = np.cumsum(0.5 * (residual[1:] + residual[:-1]) * dt)

    return {
        "mean_removed": json_float(mean_value),
        "residual_std_dps": json_float(np.std(residual)),
        "residual_slope_dps_per_h": json_float(slope_dps_per_h),
        "angle_final_deg": json_float(angle[-1]),
        "angle_p2p_deg": json_float(np.max(angle) - np.min(angle)),
        "roll60": rolling_mean_summary(residual, max(1, int(round(60.0 * fs)))),
        "roll300": rolling_mean_summary(residual, max(1, int(round(300.0 * fs)))),
    }


def analyze_axis(
    df_plateau: pd.DataFrame,
    column: str,
    fs: float,
    allan_duration_s: float,
    compute_avar: bool,
    psd_scale: float = 1.0,
) -> tuple[dict[str, object], PsdResult, AllanResult | None]:
    values = finite_values(df_plateau[column])
    mean_value = float(np.nanmean(values)) if len(values) else math.nan
    centered = values - mean_value
    std_value = float(np.nanstd(values)) if len(values) else math.nan
    rms_noise = float(math.sqrt(np.nanmean(centered * centered))) if len(values) else math.nan
    shapiro_p = shapiro_p_value(centered)
    psd = compute_psd(values, fs)
    allan = compute_allan(centered, fs, allan_duration_s) if compute_avar else None
    metric: dict[str, object] = {
        "mean": json_float(mean_value),
        "std": json_float(std_value),
        "rms_noise": json_float(rms_noise),
        "sample_count": int(len(values)),
        "shapiro_p": json_float(shapiro_p),
        "shapiro_pass": bool(math.isfinite(shapiro_p) and shapiro_p > SHAPIRO_ALPHA),
        "psd": psd_summary(psd, scale=psd_scale),
        "snr": snr_summary(mean_value, std_value),
    }
    if allan is not None:
        metric["allan"] = allan_summary(allan)
    return metric, psd, allan


def compute_axis_metrics(
    df_plateau: pd.DataFrame,
    fs: float,
    allan_duration_s: float,
) -> tuple[dict[str, dict[str, dict[str, object]]], dict[str, PsdResult], dict[str, AllanResult]]:
    metrics: dict[str, dict[str, dict[str, object]]] = {"gyro": {}, "accel": {}, "mag": {}}
    psd_results: dict[str, PsdResult] = {}
    allan_results: dict[str, AllanResult] = {}

    for axis, column in BMI_GYRO_COLUMNS.items():
        metric, psd, allan = analyze_axis(df_plateau, column, fs, allan_duration_s, compute_avar=True)
        metric["unit"] = "dps"
        metric["psd_unit"] = "dps/sqrt(Hz)"
        metric["random_walk_unit"] = "dps/sqrt(Hz)"
        mean_obj = metric["mean"]
        mean_value = float(mean_obj) if mean_obj is not None else math.nan
        metric["offset_pass"] = bool(math.isfinite(mean_value) and abs(mean_value) <= GYRO_ZRO_LIMIT_DPS)
        metric["offset_tolerance"] = GYRO_ZRO_LIMIT_DPS
        metric["residual_stability"] = gyro_residual_stability(df_plateau, column, fs, mean_value)
        metrics["gyro"][axis] = metric
        psd_results[f"gyro_{axis}"] = psd
        if allan is not None:
            allan_results[f"gyro_{axis}"] = allan

    for axis, column in BMI_ACCEL_COLUMNS.items():
        metric, psd, allan = analyze_axis(df_plateau, column, fs, allan_duration_s, compute_avar=True, psd_scale=1000.0)
        metric["unit"] = "G"
        metric["psd_unit"] = "mg/sqrt(Hz)"
        metric["random_walk_unit"] = "G/sqrt(Hz)"
        metrics["accel"][axis] = metric
        psd_results[f"accel_{axis}"] = psd
        if allan is not None:
            allan_results[f"accel_{axis}"] = allan

    accel_means = {
        axis: float(metrics["accel"][axis]["mean"]) if metrics["accel"][axis]["mean"] is not None else math.nan
        for axis in AXES
    }
    dominant_axis = max(AXES, key=lambda axis: abs(accel_means[axis]) if math.isfinite(accel_means[axis]) else -1.0)
    for axis in AXES:
        mean_value = accel_means[axis]
        expected = math.copysign(1.0, mean_value) if axis == dominant_axis and math.isfinite(mean_value) else 0.0
        error = mean_value - expected if math.isfinite(mean_value) else math.nan
        metrics["accel"][axis]["expected_static_g"] = json_float(expected)
        metrics["accel"][axis]["static_error_g"] = json_float(error)
        metrics["accel"][axis]["offset_pass"] = bool(math.isfinite(error) and abs(error) <= ACCEL_Z_LIMIT_G)
        metrics["accel"][axis]["offset_tolerance_g"] = ACCEL_Z_LIMIT_G
        metrics["accel"][axis]["dominant_gravity_axis"] = axis == dominant_axis

    for axis, column in BMM_MAG_COLUMNS.items():
        metric, psd, _ = analyze_axis(df_plateau, column, fs, allan_duration_s, compute_avar=False)
        metric["unit"] = "uT"
        metric["psd_unit"] = "uT/sqrt(Hz)"
        mean_obj = metric["mean"]
        mean_value = float(mean_obj) if mean_obj is not None else math.nan
        metric["zero_b_pass"] = bool(math.isfinite(mean_value) and abs(mean_value) <= MAG_ZERO_B_LIMIT_UT)
        metric["zero_b_tolerance_ut"] = MAG_ZERO_B_LIMIT_UT
        metrics["mag"][axis] = metric
        psd_results[f"mag_{axis}"] = psd

    return metrics, psd_results, allan_results


def compute_thermal_metrics(
    df_full: pd.DataFrame,
    fs: float,
) -> dict[str, dict[str, dict[str, object]]]:
    result: dict[str, dict[str, dict[str, object]]] = {"gyro": {}, "accel": {}}
    for group, columns, unit, limit in (
        ("gyro", BMI_GYRO_COLUMNS, "dps/degC", GYRO_TCO_LIMIT_DPS_PER_C),
        ("accel", BMI_ACCEL_COLUMNS, "G/degC", None),
    ):
        for axis, column in columns.items():
            tco = fit_tco(df_full, column, fs)
            hysteresis = compute_thermal_hysteresis(df_full, column, fs)
            axis_result: dict[str, object] = {
                "slope": json_float(tco.slope),
                "intercept": json_float(tco.intercept),
                "linear_r2": json_float(tco.linear_r2),
                "fit_degree": int(tco.fit_degree),
                "temp_span_c": json_float(tco.temp_span_c),
                "sample_count": int(tco.sample_count),
                "unit": unit,
                "hysteresis": {
                    "status": hysteresis.status,
                    "temp_overlap_c": json_float(hysteresis.temp_overlap_c),
                    "bin_count": int(hysteresis.bin_count),
                    "mean_abs_delta": json_float(hysteresis.mean_abs_delta),
                    "max_abs_delta": json_float(hysteresis.max_abs_delta),
                    "note": hysteresis.note,
                },
            }
            if limit is not None:
                axis_result["slope_pass"] = bool(math.isfinite(tco.slope) and abs(tco.slope) <= limit)
                axis_result["slope_tolerance"] = limit
            result[group][axis] = axis_result
    return result


def downsample_indices(length: int, max_points: int = 6000) -> slice:
    step = max(1, int(math.ceil(length / max_points)))
    return slice(None, None, step)


def make_dashboard(
    df_full: pd.DataFrame,
    df_plateau: pd.DataFrame,
    plateau: Plateau,
    allan: AllanResult,
    tco: TcoResult,
    axis_metrics: dict[str, dict[str, dict[str, object]]],
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(3, 2, figsize=(13, 11))
    fig.suptitle("BMI270 + BMM150 Static Validation Dashboard", fontsize=13, fontweight="bold")

    ax = axes[0, 0]
    ax.plot(df_full["time_s"], df_full["temp_c"], color="tab:orange", lw=0.9)
    ax.axvspan(plateau.start_s, plateau.end_s, color="tab:green", alpha=0.18)
    ax.set_title("Thermal Plateau Finder")
    ax.set_xlabel("time_s (s)")
    ax.set_ylabel("temp_c (°C)")
    ax.grid(True, alpha=0.25)

    ax = axes[0, 1]
    idx = downsample_indices(len(df_plateau))
    ax.scatter(
        df_plateau["time_s"].iloc[idx],
        df_plateau["bmi_gyr_x_dps"].iloc[idx],
        s=4,
        alpha=0.45,
        color="tab:blue",
        label="Gyro X ZRO",
    )
    ax.axhline(GYRO_ZRO_LIMIT_DPS, color="red", lw=0.9, ls="--")
    ax.axhline(-GYRO_ZRO_LIMIT_DPS, color="red", lw=0.9, ls="--")
    ax.set_title("ZRO / ZGO During Plateau")
    ax.set_xlabel("time_s (s)")
    ax.set_ylabel("Gyro X (dps)", color="tab:blue")
    ax.tick_params(axis="y", labelcolor="tab:blue")
    ax.grid(True, alpha=0.25)
    ax_acc = ax.twinx()
    ax_acc.scatter(
        df_plateau["time_s"].iloc[idx],
        df_plateau["bmi_acc_z_g"].iloc[idx],
        s=4,
        alpha=0.35,
        color="tab:green",
        label="Accel Z ZGO",
    )
    ax_acc.axhline(1.0 + ACCEL_Z_LIMIT_G, color="red", lw=0.9, ls=":")
    ax_acc.axhline(1.0 - ACCEL_Z_LIMIT_G, color="red", lw=0.9, ls=":")
    ax_acc.set_ylabel("Accel Z (G)", color="tab:green")
    ax_acc.tick_params(axis="y", labelcolor="tab:green")

    ax = axes[1, 0]
    if len(allan.taus) > 0:
        ax.loglog(allan.taus, allan.adev, color="tab:purple", lw=1.1, marker=".", ms=4)
        if math.isfinite(allan.bias_instability):
            ax.scatter([allan.bias_tau_s], [allan.bias_instability], color="red", zorder=3, label="Bias instability")
        if math.isfinite(allan.random_walk_density):
            tau = allan.random_walk_tau_s
            adev_at_tau = allan.random_walk_density / math.sqrt(2.0 * tau)
            ax.scatter([tau], [adev_at_tau], color="black", zorder=3, label="Random walk")
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "AVAR non disponibile", ha="center", va="center", transform=ax.transAxes)
    ax.set_title("Overlapping Allan Deviation")
    ax.set_xlabel("τ (s)")
    ax.set_ylabel("Deviation (dps)")
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1, 1]
    idx = downsample_indices(len(df_full))
    x = df_full["temp_c"].iloc[idx]
    y = df_full["bmi_gyr_x_dps"].iloc[idx]
    ax.scatter(x, y, s=4, alpha=0.28, color="tab:gray", label="FIFO samples")
    if np.all(np.isfinite(tco.fit_coeffs)):
        temp_min = float(np.nanmin(df_full["temp_c"]))
        temp_max = float(np.nanmax(df_full["temp_c"]))
        temp_line = np.linspace(temp_min, temp_max, 200)
        fit_line = np.polyval(tco.fit_coeffs, temp_line)
        label = "Linear fit" if tco.fit_degree == 1 else f"Polynomial fit deg {tco.fit_degree}"
        ax.plot(temp_line, fit_line, color="tab:red", lw=1.3, label=label)
    ax.set_title("Temperature Coefficient of Offset")
    ax.set_xlabel("temp_c (°C)")
    ax.set_ylabel("Gyro X (dps)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[2, 0]
    labels = [
        "Gx", "Gy", "Gz",
        "Ax", "Ay", "Az",
        "Mx", "My", "Mz",
    ]
    colors = (
        ["tab:blue"] * 3 +
        ["tab:green"] * 3 +
        ["tab:orange"] * 3
    )
    snr_db_values: list[float] = []
    for group in ("gyro", "accel", "mag"):
        for axis in AXES:
            snr = axis_metrics[group][axis].get("snr", {})
            value = json_float(snr.get("db") if isinstance(snr, dict) else None)
            snr_db_values.append(float(value) if value is not None else math.nan)
    plot_values = [max(-20.0, value) if math.isfinite(value) else -20.0 for value in snr_db_values]
    ax.bar(labels, plot_values, color=colors, alpha=0.8)
    ax.axhline(SNR_FAIR_DB, color="tab:red", lw=0.9, ls=":")
    ax.axhline(SNR_GOOD_DB, color="tab:orange", lw=0.9, ls=":")
    ax.axhline(SNR_EXCELLENT_DB, color="tab:green", lw=0.9, ls=":")
    ax.set_title("Static SNR by Axis")
    ax.set_ylabel("SNR (dB)")
    ax.set_ylim(-20.0, max(50.0, max(plot_values) + 5.0))
    ax.grid(True, axis="y", alpha=0.25)

    ax = axes[2, 1]
    residual = axis_metrics["gyro"]["x"].get("residual_stability", {})
    roll300 = residual.get("roll300", {}) if isinstance(residual, dict) else {}
    snr = axis_metrics["gyro"]["x"].get("snr", {})
    lines = [
        f"Gyro X SNR: {format_optional(snr.get('db') if isinstance(snr, dict) else None, 1)} dB",
        f"Gyro X rating: {snr.get('rating', 'NA') if isinstance(snr, dict) else 'NA'}",
        f"PSD slope: {format_optional(axis_metrics['gyro']['x']['psd'].get('slope_loglog'), 3)}",
        f"PSD flatness: {format_optional(axis_metrics['gyro']['x']['psd'].get('spectral_flatness'), 3)}",
        f"PSD whiteness: {axis_metrics['gyro']['x']['psd'].get('whiteness_rating', 'NA')}",
        f"Roll300 std: {format_optional(roll300.get('std') if isinstance(roll300, dict) else None, 4)} dps",
        f"Angle p2p: {format_optional(residual.get('angle_p2p_deg') if isinstance(residual, dict) else None, 2)} deg",
        "",
        "Static SNR = abs(mean plateau) / std plateau",
        "PSD whiteness from Welch estimate in log-frequency band.",
    ]
    ax.axis("off")
    ax.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", fontsize=9)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def format_float(value: float, digits: int) -> str:
    return "nan" if not math.isfinite(value) else f"{value:.{digits}f}"


def format_optional(value: object, digits: int) -> str:
    number = json_float(value)
    return "nan" if number is None else f"{number:.{digits}f}"


def timing_to_dict(timing: TimingQuality) -> dict[str, object]:
    return {
        "status": timing.status,
        "note": timing.note,
        "sample_count": timing.sample_count,
        "duration_s": json_float(timing.duration_s),
        "fs_median_hz": json_float(timing.fs_median_hz),
        "fs_mean_hz": json_float(timing.fs_mean_hz),
        "dt_median_s": json_float(timing.dt_median_s),
        "dt_mean_s": json_float(timing.dt_mean_s),
        "dt_std_s": json_float(timing.dt_std_s),
        "dt_min_s": json_float(timing.dt_min_s),
        "dt_max_s": json_float(timing.dt_max_s),
        "jitter_rms_us": json_float(timing.jitter_rms_us),
        "jitter_p95_us": json_float(timing.jitter_p95_us),
        "timing_outlier_count": timing.timing_outlier_count,
        "estimated_dropped_samples": timing.estimated_dropped_samples,
        "duplicate_time_count": timing.duplicate_time_count,
        "fifo_overrun_count": timing.fifo_overrun_count,
        "fifo_backlog_max": json_float(timing.fifo_backlog_max),
        "imu_sample_fresh_rate": json_float(timing.imu_sample_fresh_rate),
        "mag_sample_fresh_rate": json_float(timing.mag_sample_fresh_rate),
    }


def plateau_to_dict(plateau: Plateau) -> dict[str, object]:
    return {
        "found": plateau.found,
        "start_s": json_float(plateau.start_s),
        "end_s": json_float(plateau.end_s),
        "duration_s": json_float(plateau.end_s - plateau.start_s),
        "temp_mean_c": json_float(plateau.temp_mean_c),
        "median_abs_slope_c_min": json_float(plateau.median_abs_slope_c_min),
        "start_idx": plateau.start_idx,
        "end_idx": plateau.end_idx,
        "note": plateau.note,
    }


def json_clean(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): json_clean(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_clean(item) for item in value]
    if isinstance(value, np.ndarray):
        return [json_clean(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return json_clean(value.item())
    if isinstance(value, float):
        return json_float(value)
    return value


def build_json_report(
    input_path: Path,
    duration_s: float,
    fs: float,
    timing: TimingQuality,
    plateau: Plateau,
    axis_metrics: dict[str, dict[str, dict[str, object]]],
    thermal_metrics: dict[str, dict[str, dict[str, object]]],
    dashboard_path: Path | None,
) -> dict[str, object]:
    warnings: list[str] = []
    if not plateau.found:
        warnings.append("thermal plateau fallback used")
    if timing.status != "PASS":
        warnings.append(f"timing quality {timing.status}: {timing.note}")
    for group in ("gyro", "accel"):
        for axis in AXES:
            allan = axis_metrics[group][axis].get("allan", {})
            if isinstance(allan, dict) and int(allan.get("low_confidence_tau_count", 0) or 0) > 0:
                warnings.append(f"{group}_{axis} Allan has low-confidence long taus")

    report = {
        "schema_version": 1,
        "input": str(input_path.resolve()),
        "duration_s": json_float(duration_s),
        "sampling": {
            "fs_hz": json_float(fs),
            "method": "median timestamp delta",
        },
        "timing_quality": timing_to_dict(timing),
        "thermal_plateau": plateau_to_dict(plateau),
        "axis_metrics": axis_metrics,
        "thermal": thermal_metrics,
        "dashboard_png": str(dashboard_path.resolve()) if dashboard_path is not None else None,
        "warnings": warnings,
    }
    return json_clean(report)  # type: ignore[return-value]


def write_json_report(report: dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def print_timing_report(timing: TimingQuality) -> None:
    print("--- QUALITA TEMPORALE LOG ---")
    print(
        f"Timing: {timing.status} | dt median: {timing.dt_median_s * 1000.0:.3f} ms | "
        f"jitter p95: {timing.jitter_p95_us:.1f} us | drop stimati: {timing.estimated_dropped_samples}"
    )
    if timing.fifo_overrun_count is not None:
        print(
            f"FIFO overrun rows: {timing.fifo_overrun_count} | "
            f"fifo_backlog max: {format_optional(timing.fifo_backlog_max, 0)}"
        )


def print_axis_table(axis_metrics: dict[str, dict[str, dict[str, object]]]) -> None:
    print("--- BMI270 ALL AXES (Sul Plateau) ---")
    print("Gyro   mean[dps]  std[dps]  PSD[dps/√Hz]  Shapiro  Offset")
    for axis in AXES:
        metric = axis_metrics["gyro"][axis]
        psd = metric["psd"] if isinstance(metric["psd"], dict) else {}
        print(
            f"  {axis.upper()}   {format_optional(metric['mean'], 4):>9} "
            f"{format_optional(metric['std'], 4):>9} "
            f"{format_optional(psd.get('noise_floor'), 6):>12} "
            f"{format_optional(metric['shapiro_p'], 3):>8} "
            f"[{pass_fail(bool(metric['offset_pass']))}]"
        )
    print("Accel  mean[G]    std[G]    PSD[mg/√Hz]   Shapiro  Static")
    for axis in AXES:
        metric = axis_metrics["accel"][axis]
        psd = metric["psd"] if isinstance(metric["psd"], dict) else {}
        print(
            f"  {axis.upper()}   {format_optional(metric['mean'], 4):>9} "
            f"{format_optional(metric['std'], 4):>9} "
            f"{format_optional(psd.get('noise_floor'), 3):>12} "
            f"{format_optional(metric['shapiro_p'], 3):>8} "
            f"[{pass_fail(bool(metric['offset_pass']))}]"
        )


def print_tco_table(thermal_metrics: dict[str, dict[str, dict[str, object]]]) -> None:
    print("--- TCO BMI270 ALL AXES ---")
    print("Gyro   slope[dps/°C]  R2     span[°C]  Hyst mean")
    for axis in AXES:
        metric = thermal_metrics["gyro"][axis]
        hyst = metric["hysteresis"] if isinstance(metric["hysteresis"], dict) else {}
        print(
            f"  {axis.upper()}   {format_optional(metric['slope'], 5):>13} "
            f"{format_optional(metric['linear_r2'], 3):>6} "
            f"{format_optional(metric['temp_span_c'], 2):>8} "
            f"{format_optional(hyst.get('mean_abs_delta'), 5):>10}"
        )
    print("Accel  slope[G/°C]    R2     span[°C]  Hyst mean")
    for axis in AXES:
        metric = thermal_metrics["accel"][axis]
        hyst = metric["hysteresis"] if isinstance(metric["hysteresis"], dict) else {}
        print(
            f"  {axis.upper()}   {format_optional(metric['slope'], 7):>13} "
            f"{format_optional(metric['linear_r2'], 3):>6} "
            f"{format_optional(metric['temp_span_c'], 2):>8} "
            f"{format_optional(hyst.get('mean_abs_delta'), 7):>10}"
        )


def print_gyro_residual_table(axis_metrics: dict[str, dict[str, dict[str, object]]]) -> None:
    print("--- STABILITA GYRO A T COSTANTE (Media Plateau Rimossa) ---")
    print("Axis  roll60 std  roll300 std  drift[dps/h]  angle p2p[deg]")
    for axis in AXES:
        metric = axis_metrics["gyro"][axis]
        residual = metric.get("residual_stability", {})
        roll60 = residual.get("roll60", {}) if isinstance(residual, dict) else {}
        roll300 = residual.get("roll300", {}) if isinstance(residual, dict) else {}
        print(
            f"  {axis.upper()}   {format_optional(roll60.get('std'), 4):>10} "
            f"{format_optional(roll300.get('std'), 4):>11} "
            f"{format_optional(residual.get('residual_slope_dps_per_h'), 3):>12} "
            f"{format_optional(residual.get('angle_p2p_deg'), 2):>15}"
        )


def print_snr_table(axis_metrics: dict[str, dict[str, dict[str, object]]]) -> None:
    print("--- STATIC SNR (|mean plateau| / std plateau) ---")
    print("Axis   SNR[dB]   Rating")
    for group, prefix in (("gyro", "G"), ("accel", "A"), ("mag", "M")):
        for axis in AXES:
            snr = axis_metrics[group][axis].get("snr", {})
            print(
                f" {prefix}{axis.upper()}   "
                f"{format_optional(snr.get('db') if isinstance(snr, dict) else None, 1):>7}   "
                f"{snr.get('rating', 'NA') if isinstance(snr, dict) else 'NA'}"
            )


def print_psd_whiteness_table(axis_metrics: dict[str, dict[str, dict[str, object]]]) -> None:
    print("--- PSD WHITE-NOISE CHECK ---")
    print("Axis   slope    flatness   peaks   rating")
    for group, prefix in (("gyro", "G"), ("accel", "A"), ("mag", "M")):
        for axis in AXES:
            psd = axis_metrics[group][axis].get("psd", {})
            print(
                f" {prefix}{axis.upper()}   "
                f"{format_optional(psd.get('slope_loglog') if isinstance(psd, dict) else None, 3):>7}   "
                f"{format_optional(psd.get('spectral_flatness') if isinstance(psd, dict) else None, 3):>8}   "
                f"{int(psd.get('strong_peak_count', 0)) if isinstance(psd, dict) else 0:>5}   "
                f"{psd.get('whiteness_rating', 'NA') if isinstance(psd, dict) else 'NA'}"
            )


def print_allan_confidence(axis_metrics: dict[str, dict[str, dict[str, object]]]) -> None:
    print("--- CONFIDENZA AVAR ---")
    for group in ("gyro", "accel"):
        for axis in AXES:
            allan = axis_metrics[group][axis].get("allan", {})
            if not isinstance(allan, dict):
                continue
            print(
                f"{group.capitalize()} {axis.upper()}: tau={allan.get('tau_count', 0)} | "
                f"min N={format_optional(allan.get('min_equivalent_count'), 0)} | "
                f"low-conf tau={allan.get('low_confidence_tau_count', 0)}"
            )


def print_report(
    duration_s: float,
    fs: float,
    plateau: Plateau,
    stats_map: dict[str, object],
    allan: AllanResult,
    tco: TcoResult,
) -> None:
    gyro_x = stats_map["gyro_x_mean"]
    accel_z = stats_map["accel_z_mean"]
    accel_z_expected = stats_map.get("accel_z_expected_static_g", 1.0)
    accel_z_error = stats_map.get("accel_z_static_error_g", accel_z - 1.0)
    mag_x = stats_map["mag_x_mean"]
    shapiro_p = stats_map["gyro_x_shapiro_p"]

    plateau_prefix = "[+]" if plateau.found else "[!]"
    plateau_text = "Plateau Termico trovato" if plateau.found else "Plateau Termico fallback"

    print("=== REPORT VALIDAZIONE TEST STATICO ===")
    print(
        "Sensori: BMI270 & BMM150 | "
        f"Durata log: {duration_s / 3600.0:.1f} hr | "
        f"Freq: {fs:.2f} Hz (Calcolata)"
    )
    print(
        f"{plateau_prefix} {plateau_text}: da {plateau.start_s:.0f}s a {plateau.end_s:.0f}s "
        f"(Temp Media: {plateau.temp_mean_c:.1f} °C)"
    )
    print("--- ANALISI OFFSET E RUMORE (Sul Plateau) ---")
    print(
        f"Gyro X ZRO: {gyro_x:.2f} dps      "
        f"[{pass_fail(abs(gyro_x) <= GYRO_ZRO_LIMIT_DPS)}] (Tolleranza: ±0.5)"
    )
    print(
        f"Accel Z Static: {accel_z:.3f} G   "
        f"[{pass_fail(math.isfinite(accel_z_error) and abs(accel_z_error) <= ACCEL_Z_LIMIT_G)}] "
        f"(Atteso: {accel_z_expected:.0f} ± 0.02)"
    )
    print(
        f"Mag X Zero-B: {mag_x:.1f} µT     "
        f"[{pass_fail(abs(mag_x) <= MAG_ZERO_B_LIMIT_UT)}] (Tolleranza: ±40)"
    )
    print(
        f"Gyro X Shapiro-Wilk p: {format_float(shapiro_p, 2)} "
        f"[{pass_fail(math.isfinite(shapiro_p) and shapiro_p > SHAPIRO_ALPHA)}] "
        "(Rumore Gaussiano puro)"
    )
    print("--- ANALISI STOCASTICA (AVAR) ---")
    print(f"Gyro X Bias Instability: {format_float(allan.bias_instability, 3)} dps")
    print(f"Gyro X Angle Random Walk: {format_float(allan.random_walk_density, 3)} dps/√Hz")
    print("--- STABILITA GYRO A T COSTANTE ---")
    print(
        f"Gyro X roll300 std: {format_float(stats_map['gyro_x_roll300_std_dps'], 4)} dps | "
        f"Angle wander: {format_float(stats_map['gyro_x_angle_p2p_deg'], 2)} deg"
    )
    print("--- STATIC SNR ---")
    print(
        f"Accel dom SNR: {format_float(stats_map['accel_dom_snr_db'], 1)} dB [{stats_map['accel_dom_snr_rating']}] | "
        f"Gyro X SNR: {format_float(stats_map['gyro_x_snr_db'], 1)} dB [{stats_map['gyro_x_snr_rating']}]"
    )
    print("--- PSD WHITE-NOISE CHECK ---")
    print(
        f"Gyro X PSD: slope {format_float(stats_map['gyro_x_psd_slope'], 3)} | "
        f"flatness {format_float(stats_map['gyro_x_psd_flatness'], 3)} | "
        f"{stats_map['gyro_x_psd_rating']}"
    )
    print("--- DERIVA TERMICA (TCO) ---")
    print(
        f"Gyro X Slope (Drift): {format_float(tco.slope, 3)} dps/°C  "
        f"[{pass_fail(math.isfinite(tco.slope) and abs(tco.slope) <= GYRO_TCO_LIMIT_DPS_PER_C)}]"
    )


def analyze(args: argparse.Namespace) -> dict[str, object]:
    df_full = canonicalize_log(read_csv_with_fallback(args.input))
    fs = estimate_sampling_rate(df_full["time_s"])
    timing = compute_timing_quality(df_full, fs)
    duration_s = float(df_full["time_s"].iloc[-1] - df_full["time_s"].iloc[0])
    plateau = find_temperature_plateaus(
        df_full,
        fs,
        max_slope_c_min=args.plateau_slope,
        smooth_window_s=args.plateau_window_s,
        min_duration_s=args.min_plateau_s,
    )
    df_plateau = df_full.iloc[plateau.start_idx : plateau.end_idx + 1].copy()
    allan_duration_s = len(df_plateau) / fs
    axis_metrics, psd_results, allan_results = compute_axis_metrics(df_plateau, fs, allan_duration_s)
    thermal_metrics = compute_thermal_metrics(df_full, fs)

    gyro_x_values = finite_values(df_plateau[BMI_GYRO_COLUMNS["x"]])
    gyro_x_mean = axis_metrics["gyro"]["x"]["mean"]
    accel_z_mean = axis_metrics["accel"]["z"]["mean"]
    mag_x_mean = axis_metrics["mag"]["x"]["mean"]
    dominant_accel_axis = next(
        (
            axis
            for axis in AXES
            if bool(axis_metrics["accel"][axis].get("dominant_gravity_axis", False))
        ),
        "z",
    )
    gyro_x_snr = axis_metrics["gyro"]["x"].get("snr", {})
    accel_dom_snr = axis_metrics["accel"][dominant_accel_axis].get("snr", {})
    gyro_x_psd = axis_metrics["gyro"]["x"].get("psd", {})

    stats_map = {
        "gyro_x_mean": float(gyro_x_mean) if gyro_x_mean is not None else math.nan,
        "accel_z_mean": float(accel_z_mean) if accel_z_mean is not None else math.nan,
        "accel_z_expected_static_g": float(axis_metrics["accel"]["z"]["expected_static_g"])
        if axis_metrics["accel"]["z"]["expected_static_g"] is not None
        else math.nan,
        "accel_z_static_error_g": float(axis_metrics["accel"]["z"]["static_error_g"])
        if axis_metrics["accel"]["z"]["static_error_g"] is not None
        else math.nan,
        "mag_x_mean": float(mag_x_mean) if mag_x_mean is not None else math.nan,
        "gyro_x_shapiro_p": shapiro_p_value(gyro_x_values - np.nanmean(gyro_x_values)),
        "gyro_x_roll300_std_dps": float(axis_metrics["gyro"]["x"]["residual_stability"]["roll300"]["std"])
        if axis_metrics["gyro"]["x"]["residual_stability"]["roll300"]["std"] is not None
        else math.nan,
        "gyro_x_angle_p2p_deg": float(axis_metrics["gyro"]["x"]["residual_stability"]["angle_p2p_deg"])
        if axis_metrics["gyro"]["x"]["residual_stability"]["angle_p2p_deg"] is not None
        else math.nan,
        "gyro_x_snr_db": float(gyro_x_snr["db"]) if isinstance(gyro_x_snr, dict) and gyro_x_snr.get("db") is not None else math.nan,
        "gyro_x_snr_rating": gyro_x_snr.get("rating", "NA") if isinstance(gyro_x_snr, dict) else "NA",
        "accel_dom_snr_db": float(accel_dom_snr["db"]) if isinstance(accel_dom_snr, dict) and accel_dom_snr.get("db") is not None else math.nan,
        "accel_dom_snr_rating": accel_dom_snr.get("rating", "NA") if isinstance(accel_dom_snr, dict) else "NA",
        "gyro_x_psd_slope": float(gyro_x_psd["slope_loglog"]) if isinstance(gyro_x_psd, dict) and gyro_x_psd.get("slope_loglog") is not None else math.nan,
        "gyro_x_psd_flatness": float(gyro_x_psd["spectral_flatness"]) if isinstance(gyro_x_psd, dict) and gyro_x_psd.get("spectral_flatness") is not None else math.nan,
        "gyro_x_psd_rating": gyro_x_psd.get("whiteness_rating", "NA") if isinstance(gyro_x_psd, dict) else "NA",
    }

    allan = allan_results["gyro_x"]
    tco = fit_tco(df_full, BMI_GYRO_COLUMNS["x"], fs)

    print_report(duration_s, fs, plateau, stats_map, allan, tco)

    if args.verbose:
        print_timing_report(timing)
        print_axis_table(axis_metrics)
        print_gyro_residual_table(axis_metrics)
        print_snr_table(axis_metrics)
        print_psd_whiteness_table(axis_metrics)
        print_tco_table(thermal_metrics)
        print_allan_confidence(axis_metrics)
        mag_total_rms = math.sqrt(
            sum(
                float(np.nanstd(finite_values(df_plateau[col]))) ** 2
                for col in BMM_MAG_COLUMNS.values()
            )
        )
        print("--- ANALISI PSD (Welch) ---")
        print(
            "Gyro X Noise Floor: "
            f"{format_float(psd_results['gyro_x'].noise_floor, 6)} dps/√Hz | "
            f"Spikes: {', '.join(f'{f:.2f} Hz' for f in psd_results['gyro_x'].spikes_hz) or 'none'}"
        )
        print(
            "Accel Z Noise Floor: "
            f"{format_float(psd_results['accel_z'].noise_floor * 1000.0, 3)} mg/√Hz | "
            f"Spikes: {', '.join(f'{f:.2f} Hz' for f in psd_results['accel_z'].spikes_hz) or 'none'}"
        )
        print(
            "Mag Total RMS Plateau: "
            f"{format_float(mag_total_rms, 3)} µT | "
            f"Spikes: {', '.join(f'{f:.2f} Hz' for f in psd_results['mag_x'].spikes_hz) or 'none'}"
        )
        if not plateau.found and plateau.note:
            print(f"Plateau note: {plateau.note}")
        print(f"AVAR backend: {allan.source}")
        print(f"TCO linear R²: {format_float(tco.linear_r2, 3)} | fit degree: {tco.fit_degree}")

    dashboard_path: Path | None = None
    if not args.no_plot:
        out_path = args.plot_out
        if out_path is None:
            out_path = Path("Reports") / f"{args.input.stem}_bosch_static_dashboard.png"
        make_dashboard(df_full, df_plateau, plateau, allan, tco, axis_metrics, out_path)
        dashboard_path = out_path
        if args.verbose:
            print(f"Dashboard: {out_path}")

    json_path: Path | None = None
    if not args.no_json:
        json_path = args.json_out
        if json_path is None:
            json_path = Path("Reports") / f"{args.input.stem}_bosch_static_report.json"
        report = build_json_report(
            args.input,
            duration_s,
            fs,
            timing,
            plateau,
            axis_metrics,
            thermal_metrics,
            dashboard_path,
        )
        write_json_report(report, json_path)
        if args.verbose:
            print(f"JSON: {json_path}")

    return {
        "df_full": df_full,
        "df_plateau": df_plateau,
        "fs": fs,
        "timing": timing,
        "plateau": plateau,
        "axis_metrics": axis_metrics,
        "psd": psd_results,
        "allan": allan_results,
        "thermal": thermal_metrics,
        "json_path": json_path,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate static BMI270/BMM150 CSV logs with thermal plateau, PSD, AVAR, and TCO analysis."
    )
    parser.add_argument("input", type=Path, help="CSV log exported by the telemetry firmware")
    parser.add_argument("--plateau-slope", type=float, default=0.05, help="Max stable thermal slope in °C/min")
    parser.add_argument("--plateau-window-s", type=float, default=60.0, help="Moving average window for dT/dt")
    parser.add_argument("--min-plateau-s", type=float, default=300.0, help="Preferred minimum plateau duration")
    parser.add_argument("--plot-out", type=Path, default=None, help="Dashboard PNG output path")
    parser.add_argument("--json-out", type=Path, default=None, help="Machine-readable JSON output path")
    parser.add_argument("--no-plot", action="store_true", help="Skip matplotlib dashboard generation")
    parser.add_argument("--no-json", action="store_true", help="Skip machine-readable JSON report generation")
    parser.add_argument("--verbose", action="store_true", help="Print PSD diagnostics and fit metadata")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    args = build_arg_parser().parse_args(argv)
    try:
        analyze(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
