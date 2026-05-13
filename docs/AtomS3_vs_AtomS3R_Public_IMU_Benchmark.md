# M5Stack AtomS3 vs AtomS3R: Choosing the Better IMU Path

Draft for public sharing on Hackster.io or the M5Stack forum.

## 1. Context And Goal

This is not a generic winner/loser comparison. It is a practical IMU-path
selection benchmark for two M5Stack Atom devices. Vehicle telemetry with an
ESKF-style estimator is the reference application, not the only context where
the evidence is useful. It asks whether a compact IMU module can provide clean,
repeatable, bandwidth-limited gyro/accel input after logging, filtering,
startup-bias checks, and static correction.

I compared:

- M5Stack AtomS3 with MPU6886
- M5Stack AtomS3R with BMI270 + BMM150

The question was practical, not academic: which board gives the cleaner and
more reliable gyro input after the filtering, logging, and static correction
path that a real telemetry, motion-processing, or estimator pipeline would
consume?

This is not a population-level MEMS qualification. It characterizes the tested
units, firmware paths, and logging setup. The goal is to make the test method
and the results clear enough that others can repeat or challenge them.

The tested hardware was used to build a reproducible public benchmark for
compact telemetry, motion logging, field instrumentation, robotics prototyping,
and sensor-fusion workflows.

## 1.1 Practical Recommendation

- Choose AtomS3R/BMI270 if the project needs cleaner corrected gyro input,
  conservative ODR/LPF operation, validated logging, static correction, or a
  stronger path toward sensor fusion and field instrumentation.
- Use AtomS3/MPU6886 if you already have it, the project is simpler, or you are
  prepared to implement per-boot/runtime gyro bias estimation.
- Do not read this as a universal MEMS ranking. It is an application-path
  recommendation based on the tested units, firmware paths, and measured static
  evidence.

## 2. Devices Under Test

| Board | IMU | Extra Sensors / Features | Role In This Test |
| --- | --- | --- | --- |
| AtomS3 | MPU6886 | No magnetometer on this board path | Legacy/reference IMU path |
| AtomS3R | BMI270 + BMM150 | Magnetometer and PSRAM available | Candidate telemetry / sensor-fusion path |

The AtomS3R is the stronger platform on paper because it adds the BMM150
magnetometer and PSRAM. This benchmark focuses only on the IMU behavior.
Magnetometer characterization is intentionally kept separate because static
magnetic readings depend strongly on the environment.

## 3. Test Philosophy

The test is based on long static logs with the boards placed on fixed faces.
For each run, I looked for a thermally stable plateau and computed statistics
only inside that plateau.

Main checks:

- gyro bias / zero-rate output;
- gyro sample noise;
- accelerometer noise;
- bias repeatability after power-cycle;
- logging integrity;
- corrected gyro output after static/ZARU-style bias handling.

All values are computed from physical units:

- gyro in `dps`;
- accelerometer in `g`;
- temperature in `degC`.

The comparison keeps two paths separate:

1. Raw or high-bandwidth behavior.
2. Operating path behavior after low-pass filtering at about 20 Hz and 50 Hz
   sample rate.

This matters because a decimated high-bandwidth signal is not equivalent to a
signal that was bandwidth-limited before sampling.

## 4. Decision Evidence

I am not choosing BMI270 because it wins every raw metric. I am choosing the
AtomS3R/BMI270 path because, in my 50 Hz operating path with LPF, clean logging,
and static/ZARU correction, it produces a quieter and better-centered final gyro
input. In the tested MPU6886 path, a fixed X/Y bias did not transfer reliably
between same-face runs.

The short version of the result is the corrected gyro signal that would
actually reach an estimator or motion-processing pipeline, not only raw MEMS
noise.

| Sensor / case | Source | Final Mean X/Y/Z | Final Std X/Y/Z | Read |
| --- | --- | ---: | ---: | --- |
| BMI270 ODR50/LPF path + clean `tel_148` confirmation | Measured firmware output after pipeline/ZARU | about `0 / 0 / 0 dps` | `0.0068 / 0.0058 / 0.0061 dps` | Clean runtime input |
| MPU6886 fixed-bias replay | `MPU6886_014 -> MPU6886_017` | `+1.293 / +1.829 / +0.001 dps` | `0.056 / 0.041 / 0.032 dps` | Fixed X/Y bias did not transfer reliably |
| MPU6886 oracle/static replay | Same-run plateau bias on `MPU6886_017` | about `0 / 0 / 0 dps` | `0.056 / 0.041 / 0.032 dps` | Static bound only |

## 5. Raw vs Operating ODR + LPF

The before/after filtering effect is large enough that it deserves its own
read, separate from the final board choice:

This matters beyond ESKF: many practical IMU projects consume filtered/logged
data rather than raw high-bandwidth samples.

![ODR and LPF improvement summary](../reports/figures/figure_07_odr_lpf_improvement.png)

Within-sensor effect of moving from raw/high-bandwidth logs to the operating
ODR+LPF/DLPF path. This figure is not the final cross-sensor verdict.

| Sensor | Before Path | Operating Path | Gyro Std Change | Accel Std Change |
| --- | --- | --- | ---: | ---: |
| BMI270 | Raw/downsampled static logs | ODR50 + LPF20/22 | `0.9012 -> 0.0345 dps`, about **26.1x lower** | `3.98 -> 0.631 mg`, about **6.3x lower** |
| MPU6886 | Raw/high-bandwidth FIFO logs | DLPF20 + ODR50 | `0.0952 -> 0.0487 dps`, about **2.0x lower** | `1.83 -> 0.610 mg`, about **3.0x lower** |

For BMI270, the visual contrast is especially clear between a raw/downsampled
dashboard and the ODR50/LPF operating dashboard:

![BMI270 raw/downsampled dashboard example](../reports/bmi270/tel_105_bosch_static_dashboard.png)

BMI270 raw/downsampled validator dashboard. This is useful for MEMS
characterization, but it is not the estimator input path.

![BMI270 ODR50/LPF dashboard example](../reports/bmi270/tel_117_bosch_static_dashboard.png)

BMI270 ODR50/LPF validator dashboard for one strong stable-plateau run used as
operating-path sensor evidence.

Note: these BMI270 plots use the Bosch/BMI dashboard format. The MPU6886
evidence is still based on long static plateaus, but it is reported through
matching summary tables and replay artifacts rather than the same dashboard
layout.

For the static gyro decision, I use standard deviation, PSD whiteness, bias
repeatability, and corrected runtime output. The SNR panel in the BMI dashboard
is diagnostic context, not the main verdict metric.

The interpretation is not "filtered numbers always win any sensor ranking."
The interpretation is narrower: the estimator input must be judged on the
bandwidth-limited operating path, while raw/high-bandwidth logs are a separate
MEMS characterization track.

## 6. Logging And Validation

The MPU6886 was tested with a dedicated static bench firmware that writes fixed
binary records to SD. It includes:

- sequence numbers;
- CRC checks;
- FIFO diagnostics;
- SD queue/drop diagnostics;
- timestamp checks.

The BMI270 result uses the longer ODR50/LPF static logs for sensor
characterization, because they contain more meaningful thermal plateaus. For
example, `tel_117` has a roughly 50 minute plateau at about 34.9 degC and is
one of the strongest visual examples of the filtered operating path.

The later `tel_148` run is used differently: it is a logging-path confirmation,
not the primary sensor-characterization sample. It used the newer SD write
architecture and passed the timing/logging checks:

| Metric | BMI270 `tel_148` |
| --- | ---: |
| Sequence gaps | 0 |
| Estimated dropped samples | 0 |
| FIFO overrun | 0 |
| SD records dropped | 0 |

This matters because earlier BMI270 logs had timing gaps caused by the logging
path, not by BMI270 FIFO overrun. The clean `tel_148` run removes that caveat
and shows that the stronger ODR50/LPF plateau results remain comparable after
the logging path was fixed.

I do not use the `tel_148` thermal-coefficient result as a sensor verdict
because that run had an uncontrolled ambient thermal excursion. Here, `tel_148`
is used as a clean logging and runtime-output confirmation.

## 7. What Was Measured

### 7.1 Gyro Noise

In the operating path, both sensors were compared around 50 Hz sample rate with
low-pass filtering:

- BMI270: ODR50 with LPF20/22 style path.
- MPU6886: ODR50 with DLPF configuration corresponding to about 20 Hz gyro
  3 dB bandwidth and about 21.2 Hz accel bandwidth.

Operating-path gyro noise:

| Sensor | Gyro Std X/Y/Z |
| --- | ---: |
| BMI270 physical plateau, ODR50/LPF20 | about `0.0345 / 0.0355 / 0.0335 dps` |
| MPU6886 physical plateau, DLPF20/ODR50 | about `0.068 / 0.047 / 0.031 dps` |

The MPU6886 Z axis is competitive after DLPF20, but the BMI270 is quieter on
X/Y in this operating-path comparison.

### 7.2 Bias And Repeatability

Gyro bias matters more than instantaneous white noise if the bias changes after
power-cycle.

The key MPU6886 result was a same-face repeat using DLPF20:

- `MPU6886_014`: gravity on +Z
- `MPU6886_017`: same +Z face repeated later

The accelerometer means were very close, so the physical pose was effectively
the same. But the gyro plateau mean changed by:

| Axis | MPU6886 Same-Face Bias Shift |
| --- | ---: |
| X | `+1.293 dps` |
| Y | `+1.829 dps` |
| Z | `+0.001 dps` |

This is the most important result of the benchmark. The tested MPU6886 unit
cannot rely on a fixed stored X/Y gyro bias for stricter telemetry or
sensor-fusion work. It would need a per-boot or runtime bias estimator.

The BMI270 +Z repeat was much smaller:

| Axis | BMI270 Same-Face Bias Shift |
| --- | ---: |
| X | about `+0.061 dps` |
| Y | about `-0.026 dps` |
| Z | about `-0.067 dps` |

That is still not zero, but it is much more compatible with a static/ZARU bias
correction strategy.

### 7.3 Corrected Gyro Input

For my pipeline, the most useful comparison is the signal that would actually
enter the estimator after correction.

For BMI270, the clean firmware-path confirmation is measured from `tel_148`
after the current pipeline and ZARU/static correction path. This is used as a
clean logging and consistency check for the stronger ODR50/LPF plateau logs, not
as the only sensor sample:

| Sensor | Source | Final Gyro Mean X/Y/Z | Final Gyro Std X/Y/Z |
| --- | --- | ---: | ---: |
| BMI270 | Real firmware output, clean `tel_148` confirmation | about `0 / 0 / 0 dps` | `0.0068 / 0.0058 / 0.0061 dps` |

For MPU6886, I do not yet have a real firmware ESKF/ZARU output. Instead, I ran
an offline static replay:

- fixed bias from `MPU6886_014` applied to `MPU6886_017`;
- same-run plateau/oracle bias applied to `MPU6886_017`.

The fixed-bias replay left a large residual:

| Replay | Residual Mean X/Y/Z |
| --- | ---: |
| MPU6886 fixed bias `014 -> 017` | `+1.293 / +1.829 / +0.001 dps` |

The oracle same-run replay recenters the MPU6886 plateau, but this is a best
static bound, not a real firmware estimator result:

| Sensor | Source | Residual Std X/Y/Z |
| --- | --- | ---: |
| MPU6886 | Offline oracle plateau bias, `017` | `0.056 / 0.041 / 0.032 dps` |

So even with ideal static bias removal, the tested BMI270 firmware output is
about 5-9x quieter than the MPU6886 static replay bound.

## 8. Interpretation

The main lesson is that white noise is not the whole story.

The MPU6886 can look good in some noise metrics, especially on the Z axis after
DLPF20. However, on the tested AtomS3 unit, X/Y startup bias was large and not
repeatable across same-face power-cycle runs. That is a hard problem for a
stricter telemetry or sensor-fusion pipeline unless a robust runtime bias
estimator is available.

The BMI270 also has bias and needs correction, especially on raw Z, but in the
tested AtomS3R pipeline it behaved better operationally:

- long ODR50/LPF static plateaus show stable low-noise sensor behavior;
- the clean `tel_148` run removes the earlier SD/logging caveat;
- final corrected gyro centered near zero;
- low final gyro standard deviation after ZARU/static correction;
- better same-face repeatability than the tested MPU6886.

## 9. Practical Selection Guide

### Best candidate for stricter IMU workflows

For the reference vehicle-telemetry / ESKF path, and for adjacent low-rate IMU
workflows with similar logging/filtering/correction requirements,
AtomS3R/BMI270 provided the cleaner and more practical operating path.

More generally, the result suggests that the AtomS3R/BMI270 path is the
stronger candidate for compact low-rate telemetry, motion logging, field
instrumentation, and sensor-fusion experiments that depend on stable filtered
gyro input.

### Still useful for simpler or custom-calibrated workflows

I would not reject the MPU6886 universally. AtomS3/MPU6886 remains useful for
simpler IMU projects, demos, and workflows where a robust per-boot/runtime gyro
bias estimator is available.

Current preferred path:

```text
BMI270 FIFO ODR50 / LPF20 physical samples
-> mounting and static bias handling
-> ZARU/static correction during stationarity
-> ESKF covariance tuned from ODR50 static logs
```

### What would move MPU6886 forward

Based on this test, I would only use MPU6886 for stricter telemetry or
sensor-fusion work if I first validated:

- per-boot or runtime X/Y bias estimation;
- dynamic replay with corrected residual bias near zero;
- no hidden logging or FIFO issues in the final firmware path.

## 10. Limitations

This is a single-unit engineering benchmark.

Important limitations:

- It is directly validated for the tested units and the reference
  vehicle-telemetry / ESKF path.
- It is informative, not fully validated, for adjacent compact telemetry,
  motion-logging, robotics, field-instrumentation, and low-rate sensor-fusion
  workflows.
- It does not prove all MPU6886 units behave the same way.
- It does not prove all BMI270 units behave the same way.
- The MPU6886 DLPF20 fixed-bias limitation is based on the current same-face
  repeat evidence; additional 3-5 cold boots per face would make that claim
  stronger.
- It is mostly static; dynamic replay would be needed for a complete vehicle
  validation, and broader motion conclusions still need dynamic validation.
- The MPU6886 corrected result is an offline static replay, not a real firmware
  ESKF output.
- Thermal LUT or polynomial correction was not added because the available
  thermal data was not controlled enough to justify it.
- Magnetometer behavior was not part of the IMU verdict.

## 11. Feedback to M5Stack

From an application-developer perspective, the AtomS3R/BMI270 combination is
a strong candidate for compact field-instrumentation and sensor-fusion
examples when configured with conservative ODR/LPF settings and validated
logging. Future documentation examples around recommended IMU configurations
for telemetry, motion logging, and sensor-fusion use cases would be valuable
for the community.

This kind of workflow can help position M5Stack devices not only as
prototyping modules, but also as compact platforms for reproducible measurement
experiments.

## 12. Reproducible Artifacts

The compact artifacts I would share with this article are:

| Artifact | Purpose |
| --- | --- |
| `AtomS3_vs_AtomS3R_Sensor_Bench_Whitepaper.md` | Full technical whitepaper. |
| `eskf_input_quality_comparison.md/csv` | Runtime-input comparison table. |
| `mpu6886_zaru_replay_summary.md` | MPU6886 fixed-bias and oracle replay summary. |
| `MPU6886_014_vs_017_dlpf20_repeat.md` | Same-face MPU6886 repeatability result. |
| `tel_148_bmi_clean_validation_summary.md` | Clean BMI270 validation summary. |
| `build_atom_runtime_comparison.py` | Script used to generate the runtime comparison. |

Raw `.BIN` and large `.csv` logs are useful for independent verification, but
they are too large for a normal public post. They can be shared separately if
someone wants to rerun the analysis.

## 13. Disclosure / Thanks

This work was developed as part of my ongoing collaboration with M5Stack. It is
not a paid performance claim or a population-level qualification. The goal is to
turn real hardware into useful, reproducible technical feedback for compact
telemetry and sensor-fusion projects.

## 14. Conclusion

This benchmark was useful: it changed the question from "which IMU is less
noisy?" to "which IMU gives the safer corrected estimator input?"

For my vehicle-telemetry ESKF path, AtomS3R/BMI270 is the practical choice.
More generally, the result suggests that the AtomS3R/BMI270 path is the
stronger candidate for compact low-rate telemetry, motion logging, field
instrumentation, and sensor-fusion experiments that depend on stable filtered
gyro input. AtomS3/MPU6886 remains useful, especially for simpler IMU work or
workflows that implement robust per-boot/runtime gyro bias estimation.

For users, the practical takeaway is simple: choose AtomS3R/BMI270 when the IMU
path itself is part of the measurement quality problem, not just a source of raw
acceleration and gyro samples.
