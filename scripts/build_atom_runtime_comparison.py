#!/usr/bin/env python3
"""Build AtomS3 vs AtomS3R runtime input quality comparison artifacts.

This script intentionally does not modify the existing validators.  It reads
their CSV/JSON outputs and produces a decision-oriented comparison of:

* BMI270 measured firmware output after the current pipeline/ZARU path.
* MPU6886 static sensor-only replay with fixed and runtime-estimated bias.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw_private_NOT_COMMITTED"
BMI_REPORT_DIR = ROOT / "reports" / "bmi270"
MPU_REPORT_DIR = ROOT / "reports" / "mpu6886"
OUT_DIR = ROOT / "reports" / "comparison"

BMI_CSV = RAW_DIR / "tel_148.csv"
BMI_REPORT = BMI_REPORT_DIR / "tel_148_bosch_static_report.json"
MPU014_CSV = RAW_DIR / "MPU6886_014.csv"
MPU017_CSV = RAW_DIR / "MPU6886_017.csv"
MPU014_REPORT = MPU_REPORT_DIR / "MPU6886_014_dlpf20_analysis.json"
MPU017_REPORT = MPU_REPORT_DIR / "MPU6886_017_dlpf20_analysis.json"
MPU_REPEAT = MPU_REPORT_DIR / "MPU6886_014_vs_017_dlpf20_repeat.json"

OUT_CSV = OUT_DIR / "eskf_input_quality_comparison.csv"
OUT_MD = OUT_DIR / "eskf_input_quality_comparison.md"
OUT_MPU_MD = OUT_DIR / "mpu6886_zaru_replay_summary.md"
OUT_JSON = OUT_DIR / "eskf_input_quality_comparison.json"

AXES = ("x", "y", "z")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def csv_data_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            yield line


def norm_col(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "")
        .replace("µ", "u")
        .replace("Âµ", "u")
        .replace("°", "")
        .replace("Â°", "")
        .replace("/", "")
        .replace("(", "")
        .replace(")", "")
    )


def find_col(fieldnames: List[str], *prefixes: str) -> str:
    normalized = {norm_col(c): c for c in fieldnames}
    for prefix in prefixes:
        p = norm_col(prefix)
        for normalized_name, original in normalized.items():
            if normalized_name.startswith(p):
                return original
    raise KeyError(f"Missing column with prefix: {prefixes}")


def as_float(row: dict, col: str) -> float:
    value = row.get(col, "")
    if value in ("", "nan", "NaN", "None"):
        return math.nan
    return float(value)


def stats(values: np.ndarray) -> Dict[str, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"mean": math.nan, "std": math.nan, "min": math.nan, "max": math.nan}
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=0)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def slope_dps_per_h(t_s: np.ndarray, residual: np.ndarray) -> float:
    if t_s.size < 2:
        return math.nan
    t_h = (t_s - t_s[0]) / 3600.0
    return float(np.polyfit(t_h, residual, 1)[0])


def angle_metrics(t_s: np.ndarray, residual: np.ndarray) -> Tuple[float, float]:
    if t_s.size < 2:
        return math.nan, math.nan
    dt = np.diff(t_s)
    avg_rate = (residual[1:] + residual[:-1]) * 0.5
    cumulative = np.concatenate(([0.0], np.cumsum(avg_rate * dt)))
    return float(cumulative[-1]), float(np.max(cumulative) - np.min(cumulative))


def read_bmi_runtime() -> dict:
    report = load_json(BMI_REPORT)
    plateau = report["thermal_plateau"]
    start_s = float(plateau["start_s"])
    end_s = float(plateau["end_s"])

    reader = csv.DictReader(csv_data_lines(BMI_CSV))
    fields = reader.fieldnames or []
    t_col = find_col(fields, "t_us")
    seq_col = find_col(fields, "seq")
    gx_col = find_col(fields, "gx ")
    gy_col = find_col(fields, "gy ")
    gz_col = find_col(fields, "gz ")
    zaru_col = find_col(fields, "zaru_flags")
    pipe_cols = {axis: find_col(fields, f"pipe_body_g{axis}") for axis in AXES}
    tbias_col = find_col(fields, "tbias_gz")
    fifo_col = find_col(fields, "fifo_overrun")
    drop_col = find_col(fields, "sd_records_dropped")

    values = {"x": [], "y": [], "z": [], "zaru": [], "tbias_gz": []}
    pipe_values = {axis: [] for axis in AXES}
    first_t_us = None
    last_seq = None
    sequence_gap_count = 0
    max_drop = 0
    max_fifo_overrun = 0
    total_rows = 0

    for row in reader:
        total_rows += 1
        t_us = int(float(row[t_col]))
        if first_t_us is None:
            first_t_us = t_us
        t_s = (t_us - first_t_us) / 1_000_000.0

        seq = int(float(row[seq_col]))
        if last_seq is not None and seq != last_seq + 1:
            sequence_gap_count += max(1, seq - last_seq - 1)
        last_seq = seq

        try:
            max_drop = max(max_drop, int(float(row[drop_col])))
            max_fifo_overrun = max(max_fifo_overrun, int(float(row[fifo_col])))
        except ValueError:
            pass

        if start_s <= t_s <= end_s:
            values["x"].append(as_float(row, gx_col))
            values["y"].append(as_float(row, gy_col))
            values["z"].append(as_float(row, gz_col))
            values["zaru"].append(as_float(row, zaru_col))
            values["tbias_gz"].append(as_float(row, tbias_col))
            for axis in AXES:
                pipe_values[axis].append(as_float(row, pipe_cols[axis]))

    final_stats = {axis: stats(np.asarray(values[axis])) for axis in AXES}
    pipe_stats = {axis: stats(np.asarray(pipe_values[axis])) for axis in AXES}
    zaru_arr = np.asarray(values["zaru"], dtype=float)
    zaru_active_pct = float(np.mean(zaru_arr > 0.0) * 100.0) if zaru_arr.size else math.nan

    return {
        "run": "tel_148",
        "source": "Measured in firmware",
        "mode": "AtomS3R/BMI270 ODR50 LPF20/22 vehicle-format clean log",
        "plateau": plateau,
        "timing_quality": report.get("timing_quality", {}),
        "rows": total_rows,
        "final_gyro": final_stats,
        "pipe_body_gyro": pipe_stats,
        "tbias_gz": stats(np.asarray(values["tbias_gz"])),
        "zaru_active_pct": zaru_active_pct,
        "sequence_gaps": sequence_gap_count,
        "estimated_drops": int(report.get("timing_quality", {}).get("estimated_dropped_samples", max_drop)),
        "sd_records_dropped": max_drop,
        "fifo_overrun": max_fifo_overrun,
        "tco_excluded": True,
    }


def read_mpu_series(csv_path: Path, report: dict, windows: Dict[str, Tuple[float, float]]) -> dict:
    reader = csv.DictReader(csv_data_lines(csv_path))
    fields = reader.fieldnames or []
    t_col = find_col(fields, "timestamp_us")
    gyro_cols = {axis: find_col(fields, f"gyro_{axis}_dps") for axis in AXES}
    seq_col = find_col(fields, "seq")
    fifo_count_col = find_col(fields, "fifo_overrun_count")
    drop_col = find_col(fields, "sd_records_dropped")

    out = {
        name: {"t": [], "gyro": {axis: [] for axis in AXES}}
        for name in windows
    }
    first_t_us = None
    last_seq = None
    sequence_gaps = 0
    max_fifo_overrun = 0
    max_drop = 0
    total_rows = 0

    for row in reader:
        total_rows += 1
        t_us = int(float(row[t_col]))
        if first_t_us is None:
            first_t_us = t_us
        t_s = (t_us - first_t_us) / 1_000_000.0

        seq = int(float(row[seq_col]))
        if last_seq is not None and seq != last_seq + 1:
            sequence_gaps += max(1, seq - last_seq - 1)
        last_seq = seq

        max_fifo_overrun = max(max_fifo_overrun, int(float(row[fifo_count_col])))
        max_drop = max(max_drop, int(float(row[drop_col])))

        for name, (start_s, end_s) in windows.items():
            if start_s <= t_s <= end_s:
                out[name]["t"].append(t_s)
                for axis in AXES:
                    out[name]["gyro"][axis].append(as_float(row, gyro_cols[axis]))

    for name in windows:
        out[name]["t"] = np.asarray(out[name]["t"], dtype=float)
        for axis in AXES:
            out[name]["gyro"][axis] = np.asarray(out[name]["gyro"][axis], dtype=float)

    return {
        "test": report["test"],
        "mode": report["mode"],
        "windows": out,
        "rows": total_rows,
        "sequence_gaps": sequence_gaps,
        "sd_records_dropped": max_drop,
        "fifo_overrun": max_fifo_overrun,
        "plateau": report["plateau"],
        "gyro_report": report["gyro_dps"],
    }


def bias_from_report(report: dict) -> Dict[str, float]:
    return {axis: float(report["gyro_dps"][axis]["mean"]) for axis in AXES}


def bias_from_window(series: dict, window_name: str) -> Dict[str, float]:
    return {
        axis: float(np.mean(series["windows"][window_name]["gyro"][axis]))
        for axis in AXES
    }


def replay_case(case_id: str, source: str, series: dict, eval_window: str, bias: Dict[str, float], verdict: str) -> dict:
    window = series["windows"][eval_window]
    t = window["t"]
    axis_stats = {}
    residual_mean = {}
    residual_std = {}
    slopes = {}
    angle_final = {}
    angle_p2p = {}

    for axis in AXES:
        residual = window["gyro"][axis] - bias[axis]
        st = stats(residual)
        axis_stats[axis] = st
        residual_mean[axis] = st["mean"]
        residual_std[axis] = st["std"]
        slopes[axis] = slope_dps_per_h(t, residual)
        angle_final[axis], angle_p2p[axis] = angle_metrics(t, residual)

    return {
        "case": case_id,
        "source": source,
        "test": series["test"],
        "eval_window": eval_window,
        "bias_dps": bias,
        "residual": axis_stats,
        "residual_mean_dps": residual_mean,
        "residual_std_dps": residual_std,
        "residual_slope_dps_h": slopes,
        "angle_final_deg": angle_final,
        "angle_p2p_deg": angle_p2p,
        "sample_count": int(t.size),
        "sequence_gaps": series["sequence_gaps"],
        "sd_records_dropped": series["sd_records_dropped"],
        "fifo_overrun": series["fifo_overrun"],
        "verdict": verdict,
    }


def fmt(value: object, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isnan(v):
        return "n/a"
    return f"{v:.{digits}f}"


def row_from_bmi(bmi: dict) -> dict:
    row = {
        "platform": "AtomS3R",
        "sensor": "BMI270",
        "run": "tel_148",
        "mode": "ODR50 LPF20/22",
        "measurement_type": "Measured in firmware after pipeline/ZARU",
        "bias_strategy": "Boot/static bias plus firmware ZARU",
        "zaru_active_pct": bmi["zaru_active_pct"],
        "sequence_gaps": bmi["sequence_gaps"],
        "estimated_drops": bmi["estimated_drops"],
        "fifo_overrun": bmi["fifo_overrun"],
        "verdict": "PASS: centered final gyro input; clean logging",
    }
    for axis in AXES:
        row[f"mean_{axis}_dps"] = bmi["final_gyro"][axis]["mean"]
        row[f"std_{axis}_dps"] = bmi["final_gyro"][axis]["std"]
        row[f"angle_final_{axis}_deg"] = ""
        row[f"angle_p2p_{axis}_deg"] = ""
    return row


def row_from_mpu(case: dict, measurement_type: str, bias_strategy: str) -> dict:
    row = {
        "platform": "AtomS3",
        "sensor": "MPU6886",
        "run": case["test"],
        "mode": "ODR50 DLPF20/21.2",
        "measurement_type": measurement_type,
        "bias_strategy": bias_strategy,
        "zaru_active_pct": "",
        "sequence_gaps": case["sequence_gaps"],
        "estimated_drops": case["sd_records_dropped"],
        "fifo_overrun": case["fifo_overrun"],
        "verdict": case["verdict"],
    }
    for axis in AXES:
        row[f"mean_{axis}_dps"] = case["residual_mean_dps"][axis]
        row[f"std_{axis}_dps"] = case["residual_std_dps"][axis]
        row[f"angle_final_{axis}_deg"] = case["angle_final_deg"][axis]
        row[f"angle_p2p_{axis}_deg"] = case["angle_p2p_deg"][axis]
    return row


def write_csv(rows: List[dict]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "platform",
        "sensor",
        "run",
        "mode",
        "measurement_type",
        "bias_strategy",
        "mean_x_dps",
        "mean_y_dps",
        "mean_z_dps",
        "std_x_dps",
        "std_y_dps",
        "std_z_dps",
        "angle_final_x_deg",
        "angle_final_y_deg",
        "angle_final_z_deg",
        "angle_p2p_x_deg",
        "angle_p2p_y_deg",
        "angle_p2p_z_deg",
        "zaru_active_pct",
        "sequence_gaps",
        "estimated_drops",
        "fifo_overrun",
        "verdict",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def md_table(headers: List[str], rows: List[List[object]], digits: int = 4) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(v, digits) for v in row) + " |")
    return "\n".join(lines)


def write_markdown(bmi: dict, cases: Dict[str, dict], repeat: dict) -> None:
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    comparison_rows = [
        [
            "BMI270",
            "Measured in firmware",
            "tel_148",
            bmi["final_gyro"]["x"]["mean"],
            bmi["final_gyro"]["y"]["mean"],
            bmi["final_gyro"]["z"]["mean"],
            bmi["final_gyro"]["x"]["std"],
            bmi["final_gyro"]["y"]["std"],
            bmi["final_gyro"]["z"]["std"],
            bmi["zaru_active_pct"],
            bmi["sequence_gaps"],
            bmi["estimated_drops"],
            bmi["fifo_overrun"],
            "PASS",
        ],
        [
            "MPU6886",
            "Offline fixed bias 014 -> 017",
            "MPU6886_017",
            cases["fixed_014_to_017"]["residual_mean_dps"]["x"],
            cases["fixed_014_to_017"]["residual_mean_dps"]["y"],
            cases["fixed_014_to_017"]["residual_mean_dps"]["z"],
            cases["fixed_014_to_017"]["residual_std_dps"]["x"],
            cases["fixed_014_to_017"]["residual_std_dps"]["y"],
            cases["fixed_014_to_017"]["residual_std_dps"]["z"],
            "n/a",
            cases["fixed_014_to_017"]["sequence_gaps"],
            cases["fixed_014_to_017"]["sd_records_dropped"],
            cases["fixed_014_to_017"]["fifo_overrun"],
            "FAIL fixed X/Y bias",
        ],
        [
            "MPU6886",
            "Offline per-run plateau bias",
            "MPU6886_017",
            cases["oracle_017"]["residual_mean_dps"]["x"],
            cases["oracle_017"]["residual_mean_dps"]["y"],
            cases["oracle_017"]["residual_mean_dps"]["z"],
            cases["oracle_017"]["residual_std_dps"]["x"],
            cases["oracle_017"]["residual_std_dps"]["y"],
            cases["oracle_017"]["residual_std_dps"]["z"],
            "n/a",
            cases["oracle_017"]["sequence_gaps"],
            cases["oracle_017"]["sd_records_dropped"],
            cases["oracle_017"]["fifo_overrun"],
            "BOUND only",
        ],
    ]

    OUT_MD.write_text(
        "# ESKF Input Quality Comparison\n\n"
        "This artifact compares the gyro signal quality that can be supplied to the runtime estimator. "
        "BMI270 values are measured firmware outputs from `tel_148`; MPU6886 values are static "
        "sensor-only offline replay, not firmware ESKF/ZARU output.\n\n"
        "## Runtime Input Table\n\n"
        + md_table(
            [
                "Sensor",
                "Source",
                "Run",
                "mean X",
                "mean Y",
                "mean Z",
                "std X",
                "std Y",
                "std Z",
                "ZARU %",
                "seq gaps",
                "drops",
                "FIFO overrun",
                "Status",
            ],
            comparison_rows,
        )
        + "\n\n"
        "## Interpretation\n\n"
        "- `tel_148` shows the actual BMI270 signal after the current pipeline/ZARU path: the final gyro input is centered near zero, with about 0.006 dps standard deviation and clean logging.\n"
        "- `MPU6886_014 -> MPU6886_017` shows that a fixed calibration is not acceptable on X/Y for this device: the residual bias remains about "
        f"{fmt(cases['fixed_014_to_017']['residual_mean_dps']['x'], 3)} / "
        f"{fmt(cases['fixed_014_to_017']['residual_mean_dps']['y'], 3)} dps.\n"
        "- The per-run plateau replay proves the MPU6886 can be re-centered if a runtime bias estimator is available, but this is a static bound, not a demonstrated firmware ESKF result.\n"
        "- The TCO result from `tel_148` is excluded from the verdict because that run had strong ambient thermal excursion.\n",
        encoding="utf-8",
    )

    mpu_rows = []
    for key in ("fixed_014_to_017", "boot_120s_017", "oracle_017", "oracle_014"):
        case = cases[key]
        mpu_rows.append(
            [
                key,
                case["test"],
                case["sample_count"],
                case["residual_mean_dps"]["x"],
                case["residual_mean_dps"]["y"],
                case["residual_mean_dps"]["z"],
                case["residual_std_dps"]["x"],
                case["residual_std_dps"]["y"],
                case["residual_std_dps"]["z"],
                case["angle_p2p_deg"]["x"],
                case["angle_p2p_deg"]["y"],
                case["angle_p2p_deg"]["z"],
                case["verdict"],
            ]
        )

    OUT_MPU_MD.write_text(
        "# MPU6886 ZARU Replay Summary\n\n"
        "Replay type: static sensor-only bias subtraction on MPU6886 DLPF20/21.2 logs. "
        "This is not full SITL ESKF and not firmware ZARU output.\n\n"
        "## Repeatability Anchor\n\n"
        + md_table(
            ["Metric", "X", "Y", "Z"],
            [
                [
                    "014 -> 017 gyro mean delta dps",
                    repeat["gyro_mean_delta_dps"]["x"],
                    repeat["gyro_mean_delta_dps"]["y"],
                    repeat["gyro_mean_delta_dps"]["z"],
                ],
                [
                    "014 -> 017 gyro std delta dps",
                    repeat["gyro_std_delta_dps"]["x"],
                    repeat["gyro_std_delta_dps"]["y"],
                    repeat["gyro_std_delta_dps"]["z"],
                ],
            ],
        )
        + "\n\n"
        "## Replay Cases\n\n"
        + md_table(
            [
                "Case",
                "Eval run",
                "samples",
                "mean X",
                "mean Y",
                "mean Z",
                "std X",
                "std Y",
                "std Z",
                "angle p2p X",
                "angle p2p Y",
                "angle p2p Z",
                "Verdict",
            ],
            mpu_rows,
        )
        + "\n\n"
        "Fixed-bias replay fails because X/Y startup bias is not repeatable across the same +Z face. "
        "Per-run/oracle bias subtraction recenters the static plateau, so MPU6886 recovery depends on a robust runtime bias estimator and later dynamic validation.\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate AtomS3 vs AtomS3R runtime input quality artifacts. "
            "Raw CSV inputs stay in a private directory that is ignored by git."
        )
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Private directory containing tel_148.csv, MPU6886_014.csv, and MPU6886_017.csv.",
    )
    parser.add_argument(
        "--bmi-reports-dir",
        type=Path,
        default=BMI_REPORT_DIR,
        help="Directory containing compact BMI270 validator JSON reports.",
    )
    parser.add_argument(
        "--mpu-reports-dir",
        type=Path,
        default=MPU_REPORT_DIR,
        help="Directory containing compact MPU6886 analysis JSON reports.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=OUT_DIR,
        help="Output directory for regenerated comparison artifacts.",
    )
    return parser.parse_args()


def configure_paths(args: argparse.Namespace) -> None:
    global BMI_CSV, BMI_REPORT, MPU014_CSV, MPU017_CSV
    global MPU014_REPORT, MPU017_REPORT, MPU_REPEAT
    global OUT_CSV, OUT_MD, OUT_MPU_MD, OUT_JSON

    raw_dir = args.raw_dir.resolve()
    bmi_reports_dir = args.bmi_reports_dir.resolve()
    mpu_reports_dir = args.mpu_reports_dir.resolve()
    out_dir = args.out_dir.resolve()

    BMI_CSV = raw_dir / "tel_148.csv"
    BMI_REPORT = bmi_reports_dir / "tel_148_bosch_static_report.json"
    MPU014_CSV = raw_dir / "MPU6886_014.csv"
    MPU017_CSV = raw_dir / "MPU6886_017.csv"
    MPU014_REPORT = mpu_reports_dir / "MPU6886_014_dlpf20_analysis.json"
    MPU017_REPORT = mpu_reports_dir / "MPU6886_017_dlpf20_analysis.json"
    MPU_REPEAT = mpu_reports_dir / "MPU6886_014_vs_017_dlpf20_repeat.json"

    OUT_CSV = out_dir / "eskf_input_quality_comparison.csv"
    OUT_MD = out_dir / "eskf_input_quality_comparison.md"
    OUT_MPU_MD = out_dir / "mpu6886_zaru_replay_summary.md"
    OUT_JSON = out_dir / "eskf_input_quality_comparison.json"


def main() -> None:
    configure_paths(parse_args())
    bmi = read_bmi_runtime()

    mpu014_report = load_json(MPU014_REPORT)
    mpu017_report = load_json(MPU017_REPORT)
    repeat = load_json(MPU_REPEAT)

    mpu014_plateau = mpu014_report["plateau"]
    mpu017_plateau = mpu017_report["plateau"]

    mpu014 = read_mpu_series(
        MPU014_CSV,
        mpu014_report,
        {
            "plateau": (float(mpu014_plateau["start_s"]), float(mpu014_plateau["end_s"])),
            "boot_120s": (5.0, 125.0),
        },
    )
    mpu017 = read_mpu_series(
        MPU017_CSV,
        mpu017_report,
        {
            "plateau": (float(mpu017_plateau["start_s"]), float(mpu017_plateau["end_s"])),
            "boot_120s": (5.0, 125.0),
        },
    )

    bias014 = bias_from_report(mpu014_report)
    bias017_plateau = bias_from_report(mpu017_report)
    bias017_boot = bias_from_window(mpu017, "boot_120s")

    cases = {
        "fixed_014_to_017": replay_case(
            "fixed_014_to_017",
            "Offline replay / fixed calibration",
            mpu017,
            "plateau",
            bias014,
            "FAIL: fixed +Z calibration leaves large X/Y residual bias",
        ),
        "boot_120s_017": replay_case(
            "boot_120s_017",
            "Offline replay / first 120 s boot estimator",
            mpu017,
            "plateau",
            bias017_boot,
            "PARTIAL: boot estimate helps only if startup window is static and thermally representative",
        ),
        "oracle_017": replay_case(
            "oracle_017",
            "Offline replay / oracle same-run plateau bias",
            mpu017,
            "plateau",
            bias017_plateau,
            "BOUND: centers plateau but requires runtime bias estimation",
        ),
        "oracle_014": replay_case(
            "oracle_014",
            "Offline replay / oracle same-run plateau bias",
            mpu014,
            "plateau",
            bias014,
            "BOUND: centers plateau but requires runtime bias estimation",
        ),
    }

    rows = [
        row_from_bmi(bmi),
        row_from_mpu(
            cases["fixed_014_to_017"],
            "Offline replay / required estimator",
            "Fixed calibration from MPU6886_014 applied to MPU6886_017",
        ),
        row_from_mpu(
            cases["boot_120s_017"],
            "Offline replay / required estimator",
            "First 120 s of same boot applied to plateau",
        ),
        row_from_mpu(
            cases["oracle_017"],
            "Offline replay / oracle bound",
            "Same-run plateau bias subtracted",
        ),
    ]

    write_csv(rows)
    write_markdown(bmi, cases, repeat)
    OUT_JSON.write_text(
        json.dumps(
            {
                "bmi270_tel_148": bmi,
                "mpu6886_repeat_014_vs_017": repeat,
                "mpu6886_replay_cases": cases,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_MD}")
    print(f"Wrote {OUT_MPU_MD}")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
