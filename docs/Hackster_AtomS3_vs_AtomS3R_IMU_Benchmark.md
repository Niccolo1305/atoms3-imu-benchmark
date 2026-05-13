# M5Stack AtomS3 vs AtomS3R: Choosing the Better IMU Path

![AtomS3 vs AtomS3R IMU benchmark cover](assets/hackster_hero.png)

Product images in the cover are from the official M5Stack documentation. The
cover chart is an illustrative summary; the measured decision evidence is in
the runtime-input table below.

This project is not a generic winner/loser comparison. It is a practical
IMU-path selection benchmark for two M5Stack Atom devices. Vehicle telemetry
with an ESKF-style estimator is the reference application, not the only context
where the evidence is useful. The benchmark asks whether a compact IMU module
can provide clean, repeatable, bandwidth-limited gyro/accel input after logging,
filtering, startup-bias checks, and static correction.

I compared:

- **AtomS3** with the **MPU6886**
- **AtomS3R** with the **BMI270 + BMM150**

The question was practical: which board gives the cleaner and more reliable
gyro input after the filtering, logging, and static correction path that a
real telemetry, motion-processing, or estimator pipeline would consume?

I am not choosing BMI270 because it wins every raw metric. I am choosing the
AtomS3R/BMI270 path because, in my 50 Hz operating path with LPF, clean
logging, and static/ZARU correction, it produces a quieter and better-centered
final gyro input. In the tested MPU6886 path, a fixed X/Y bias did not transfer
reliably between same-face runs.

This is not a population-level MEMS qualification. It is a single-unit,
firmware-path benchmark. The result is useful because it exposes the failure
modes that matter when IMU data enters a logged, filtered, and corrected
motion-processing pipeline, but it should not be read as a universal claim
about every MPU6886 or every BMI270.

The tested hardware was used to build a reproducible public benchmark for
compact telemetry, motion logging, field instrumentation, robotics prototyping,
and sensor-fusion workflows.

## Why this benchmark matters

M5Stack devices are often used in fast prototyping, compact telemetry, motion
logging, robotics experiments, and field instrumentation. For these workflows,
the practical value of an IMU module is not only the sensor name or raw noise.
It is whether the full acquisition path produces stable, logged, corrected, and
bandwidth-limited data.

That means checking the details that usually decide whether an IMU path is
usable in practice: ODR and LPF configuration, logging integrity, startup-bias
repeatability, and static/ZARU-style correction.

## What I wanted to demonstrate

- Reproducible testing rather than a quick sensor trial.
- A clear split between raw metrics, runtime behavior, and the application
  decision.
- A practical board/path selection guide for users choosing between AtomS3 and
  AtomS3R.
- A reusable validation pattern, backed by public artifacts: figures, scripts,
  firmware, reports, and a repo.

## Practical recommendation

- Choose **AtomS3R/BMI270** if the project needs cleaner corrected gyro input,
  conservative ODR/LPF operation, validated logging, static correction, or a
  stronger path toward sensor fusion and field instrumentation.
- Use **AtomS3/MPU6886** if you already have it, the project is simpler, or you
  are prepared to implement per-boot/runtime gyro bias estimation.
- Do not read this as a universal MEMS ranking. It is an application-path
  recommendation based on the tested units, firmware paths, and measured static
  evidence.

## Decision evidence

The short version of the result is the corrected gyro signal that would
actually reach an estimator or motion-processing pipeline, not only raw MEMS
noise.

| Sensor / case | Source | Mean residual X/Y/Z (dps) | Std X/Y/Z (dps) | Read |
| --- | --- | ---: | ---: | --- |
| BMI270 ODR50/LPF path + clean `tel_148` confirmation | Measured firmware output after pipeline/ZARU | about `0 / 0 / 0 dps` | `0.0068 / 0.0058 / 0.0061 dps` | Clean runtime input, consistent with stronger plateau logs |
| MPU6886 fixed-bias replay | `MPU6886_014 -> MPU6886_017` | `+1.293 / +1.829 / +0.001 dps` | `0.056 / 0.041 / 0.032 dps` | Fixed X/Y bias did not transfer reliably in my tested unit |
| MPU6886 oracle/static replay | Same-run plateau bias on `MPU6886_017` | about `0 / 0 / 0 dps` | `0.056 / 0.041 / 0.032 dps` | Best static bound, not firmware ESKF output |

Even under ideal static MPU6886 bias removal, the BMI270 measured runtime input
is about **5-9x quieter** in this benchmark. The `tel_148` number is used here
as a clean firmware-path confirmation, not as the single representative sensor
plateau.

## Devices under test

| Board | IMU path | Other relevant hardware | Role in this test |
| --- | --- | --- | --- |
| M5Stack AtomS3 | MPU6886 | No magnetometer in this path | Existing/reference IMU path |
| M5Stack AtomS3R | BMI270 + BMM150 | BMM150 magnetometer, PSRAM | Candidate telemetry / sensor-fusion path |

The magnetometer is listed because it is part of the AtomS3R hardware, but it is
not part of the IMU verdict below. Static magnetometer behavior depends heavily
on local magnetic conditions, so I kept it separate from the gyro/accelerometer
comparison.

## Test philosophy

The benchmark uses long static logs with each board placed in fixed physical
orientations. For each run, the analysis selects a thermally stable plateau
rather than computing statistics over the whole warm-up.

Core method choices:

- Static, long-duration tests on fixed board faces.
- Thermal plateau selection before computing bias, drift, and noise metrics.
- Physical units throughout: gyro in `dps`, acceleration in `g` or `mg`, and
  temperature in `degC`.
- A 50 Hz operating path, because that is the intended estimator input rate.
- Hardware low-pass filtering around 20 Hz: BMI270 ODR50/LPF20-style path and
  MPU6886 DLPF20/ODR50 path.
- Logging integrity checks: sequence gaps, estimated dropped samples, FIFO
  overrun, and SD-write/drop diagnostics.
- No raw GPS data is published.

The 20 Hz LPF detail matters. A raw high-bandwidth signal decimated to 50 Hz is
not the same thing as a signal bandwidth-limited before sampling. For an
estimator or motion-processing input-quality decision, I care most about the
filtered operating path.

## Raw vs ODR + LPF

The largest noise change in the study is not only the choice of board. It is
the move from raw/high-bandwidth data to the operating ODR + LPF path. That
effect appears on both sensors, so I kept raw and filtered numbers separate.
This matters beyond ESKF: many practical IMU projects consume filtered/logged
data rather than raw high-bandwidth samples.

![ODR and LPF improvement summary](../reports/figures/figure_07_odr_lpf_improvement.png)

Within-sensor effect of moving from raw/high-bandwidth logs to the operating
ODR+LPF/DLPF path. This figure is not the final cross-sensor verdict.

| Sensor | Before path | Operating path | Gyro std change | Accel std change |
| --- | --- | --- | ---: | ---: |
| BMI270 | Raw/downsampled static logs | ODR50 + LPF20/22 | `0.9012 -> 0.0345 dps`, about **26.1x lower** | `3.98 -> 0.631 mg`, about **6.3x lower** |
| MPU6886 | Raw/high-bandwidth FIFO logs | DLPF20 + ODR50 | `0.0952 -> 0.0487 dps`, about **2.0x lower** | `1.83 -> 0.610 mg`, about **3.0x lower** |

The BMI270 dashboards make the raw-vs-filtered difference visually obvious:

![BMI270 raw/downsampled dashboard example](../reports/bmi270/tel_105_bosch_static_dashboard.png)

BMI270 raw/downsampled validator dashboard. This is useful for MEMS
characterization, but it is not the estimator input path.

![BMI270 ODR50/LPF dashboard example](../reports/bmi270/tel_117_bosch_static_dashboard.png)

BMI270 ODR50/LPF validator dashboard for one strong stable-plateau run used as
operating-path sensor evidence.

Note: these BMI270 plots use the Bosch/BMI dashboard format. MPU6886 evidence
is reported through matching plateau summaries and replay artifacts rather than
the same dashboard layout. For the static gyro decision, I use standard
deviation, PSD whiteness, bias repeatability, and corrected runtime output; the
SNR panel is diagnostic context, not the main verdict metric.

This is why the final decision is based on operating-path evidence. Raw sample
noise is useful context, but the target estimator or motion-processing pipeline
will not consume the raw/high-bandwidth signal directly.

## Firmware and analysis pipeline

![Benchmark pipeline](assets/hackster_pipeline.png)

Conceptual benchmark pipeline. The evidence is intentionally asymmetric: BMI270
includes a measured firmware path plus clean-log confirmation, while MPU6886
uses a dedicated static bench and offline replay rather than a demonstrated
firmware ESKF/ZARU output.

The two boards were not tested with a single generic sketch. Each path used the
firmware or replay route that best matched the question being asked.

| Component | What it did |
| --- | --- |
| Dedicated MPU6886 static bench firmware | Logged MPU6886 FIFO data to SD with fixed-size records, CRC, sequence numbers, timing checks, and FIFO/SD diagnostics. It does not include GPS, ESKF, ZARU, axis rotation, or a calibration layer. |
| AtomS3R telemetry logging path | Logged BMI270 physical columns through the current AtomS3R telemetry logging firmware path. |
| Bosch/BMI static validator | Checked BMI270 plateau statistics, PSD/whiteness, noise, bias, and logging health. |
| Offline runtime comparison script | Rebuilt the runtime input comparison from private raw CSV/BIN sources into compact public reports. |
| ZARU/static correction concept | During stationarity, the pipeline estimates or suppresses residual gyro bias so the estimator sees a centered gyro input. |

For BMI270, sensor behavior comes from the stronger ODR50/LPF static plateau
logs and runtime input is confirmed with clean firmware output. For MPU6886,
the corrected result is an offline static sensor-only replay: useful as a bound,
but not a demonstrated firmware ESKF result.

## Key Results

The BMI270 result is built from two evidence layers. The stronger ODR50/LPF20-22
static logs characterize sensor behavior; for example, `tel_117` has a roughly
50 minute plateau and filtered gyro standard deviation of about
`0.0346 / 0.0362 / 0.0335 dps` on X/Y/Z, with WHITE gyro PSD behavior.

`tel_148` is used differently: it is the clean logging confirmation run, not
the primary sensor-characterization sample. It shows that the later AtomS3R
firmware path fixed the SD/logging caveat while preserving comparable BMI270
behavior.

| Logging metric | BMI270 `tel_148` |
| --- | ---: |
| Sequence gaps | 0 |
| Estimated dropped samples | 0 |
| FIFO overrun | 0 |

I do not use the `tel_148` thermal-coefficient result as a sensor verdict
because that run had an uncontrolled ambient thermal excursion. Here, `tel_148`
is used as a clean logging and runtime-output confirmation.

The MPU6886 fixed-bias replay changed the decision. Applying the
`MPU6886_014` +Z bias to the later same-face `MPU6886_017` run leaves a large
X/Y residual:

| MPU6886 same-face DLPF20 repeat | X | Y | Z |
| --- | ---: | ---: | ---: |
| `017 - 014` gyro mean delta | `+1.293 dps` | `+1.829 dps` | `+0.001 dps` |

The accelerometer means were close, so this points more toward startup-bias
repeatability than a large pose mistake.

For broader context, these figures from the repository summarize the noise and
Allan-style behavior used in the whitepaper:

![Noise comparison figure](../reports/figures/figure_02_noise_comparison.png)

![Allan deviation figure](../reports/figures/figure_05_allan_deviation.png)

These figures are context for noise and stability behavior, not the final
winner/loser metric. The decision is based on the operating-path runtime input,
logging integrity, and bias-correction behavior.

## Interpretation

White noise is not the whole story.

After DLPF20, the tested MPU6886 is not simply "noisy." Its Z-axis filtered
noise and stability remain interesting. The blocker for my ESKF-style pipeline
is X/Y startup-bias repeatability: a fixed stored bias from one static run did
not transfer well to a later same-face run.

That matters more than raw sample noise because static gyro bias integrates
directly into angle error.

For simple IMU demos, both devices can be useful. The difference becomes
important when the IMU is part of a longer measurement chain where startup
bias, bandwidth, logging integrity, and correction behavior matter.

The AtomS3R/BMI270 path is operationally stronger in this tested setup because:

- the ODR50/LPF static logs provide stronger long-plateau sensor evidence;
- `tel_148` confirms that the later firmware path has clean logging diagnostics;
- the operating path is already 50 Hz with LPF around 20 Hz;
- ZARU/static correction keeps the final gyro input centered near zero;
- the final corrected gyro standard deviation is around `0.006 dps` per axis.

The MPU6886 may still be recoverable, but for stricter telemetry or
sensor-fusion work it would need robust per-boot or runtime X/Y bias
estimation, followed by dynamic validation. The offline oracle replay shows
that static re-centering is possible; it does not prove the full firmware path
is already solved.

## Practical Selection Guide

### Best candidate for stricter IMU workflows

For the reference vehicle-telemetry / ESKF path, and for adjacent low-rate IMU
workflows with similar logging/filtering/correction requirements,
**AtomS3R/BMI270** is the more practical IMU path in this benchmark.

More generally, the result suggests that the AtomS3R/BMI270 path is the
stronger candidate for compact low-rate telemetry, motion logging, field
instrumentation, and sensor-fusion experiments that depend on stable filtered
gyro input.

### Still useful for simpler or custom-calibrated workflows

I am not treating this as a universal MPU6886 verdict, and I am not claiming
that BMI270 wins every possible sensor benchmark. AtomS3/MPU6886 remains useful
for simpler IMU projects, demos, and workflows where a robust per-boot/runtime
gyro bias estimator is available.

### What would move MPU6886 forward

In my tested unit and firmware path, the practical blocker is X/Y startup-bias
repeatability. I would move the AtomS3/MPU6886 path forward for stricter
telemetry or sensor-fusion work only after validating robust per-boot/runtime
X/Y bias estimation plus dynamic validation.

## Limitations

Important limits of this benchmark:

- It is directly validated for the tested units and the reference
  vehicle-telemetry / ESKF path.
- It is informative, not fully validated, for adjacent compact telemetry,
  motion-logging, robotics, field-instrumentation, and low-rate sensor-fusion
  workflows.
- It is a single-unit comparison, not a population study.
- The MPU6886 DLPF20 fixed-bias limitation is based on the current same-face
  repeat evidence; additional 3-5 cold boots per face would make that claim
  stronger.
- It is mostly static; a complete vehicle decision still benefits from dynamic
  replay or road testing, and broader motion conclusions still need dynamic
  validation.
- The MPU6886 corrected result is an offline static sensor-only replay, not a
  firmware ESKF output.
- Magnetometer behavior is not part of the IMU verdict.
- Raw GPS/vehicle logs are not published.
- Thermal behavior was observed through plateau selection, but this is not a
  controlled thermal-chamber characterization.

## Feedback to M5Stack

From an application-developer perspective, the AtomS3R/BMI270 combination is
a strong candidate for compact field-instrumentation and sensor-fusion
examples when configured with conservative ODR/LPF settings and validated
logging. Future documentation examples around recommended IMU configurations
for telemetry, motion logging, and sensor-fusion use cases would be valuable
for the community.

This kind of workflow can help position M5Stack devices not only as
prototyping modules, but also as compact platforms for reproducible measurement
experiments.

## Reproducibility / GitHub Repo

The repository is organized so readers can inspect the public reports without
needing the private raw logs. The full whitepaper goes deeper than this article,
and the runtime comparison can be regenerated from private raw files with:

```powershell
python .\scripts\build_atom_runtime_comparison.py
```

Start here:

- GitHub repository: [GitHub repo](https://github.com/Niccolo1305/atoms3-imu-benchmark)
- Full technical whitepaper: `docs/AtomS3_vs_AtomS3R_Sensor_Bench_Whitepaper.md`

## Code and Data Availability

The GitHub repo contains the public evidence package: compact reports,
dashboards, figures, scripts, documentation, and the dedicated MPU6886 static
bench firmware.

Raw `.BIN` captures and large raw `.csv` files are excluded for size and
privacy. If the private raw files are placed in
`data/raw_private_NOT_COMMITTED/`, the comparison artifacts can be regenerated
with the script above. No raw GPS/vehicle logs are published.

## Disclosure / Thanks

This work was developed as part of my ongoing collaboration with M5Stack. It is
not a paid performance claim or a population-level qualification. The goal is to
turn real hardware into useful, reproducible technical feedback for compact
telemetry and sensor-fusion projects.

## Conclusion

For my vehicle-telemetry ESKF path, AtomS3R/BMI270 is the practical choice.
More generally, the result suggests that the AtomS3R/BMI270 path is the
stronger candidate for compact low-rate telemetry, motion logging, field
instrumentation, and sensor-fusion experiments that depend on stable filtered
gyro input. AtomS3/MPU6886 remains useful, especially for simpler IMU work or
workflows that implement robust per-boot/runtime gyro bias estimation.

For users, the practical takeaway is simple: choose AtomS3R/BMI270 when the IMU
path itself is part of the measurement quality problem, not just a source of raw
acceleration and gyro samples.
