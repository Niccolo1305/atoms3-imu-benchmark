# ESKF Input Quality Comparison

This artifact compares the gyro signal quality that can be supplied to the runtime estimator. BMI270 values are measured firmware outputs from `tel_148`; MPU6886 values are static sensor-only offline replay, not firmware ESKF/ZARU output.

## Runtime Input Table

| Sensor | Source | Run | mean X | mean Y | mean Z | std X | std Y | std Z | ZARU % | seq gaps | drops | FIFO overrun | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BMI270 | Measured in firmware | tel_148 | -0.0000 | -0.0000 | 0.0000 | 0.0068 | 0.0058 | 0.0061 | 99.4381 | 0 | 0 | 0 | PASS |
| MPU6886 | Offline fixed bias 014 -> 017 | MPU6886_017 | 1.2935 | 1.8292 | 0.0008 | 0.0563 | 0.0415 | 0.0318 | n/a | 0 | 0 | 0 | FAIL fixed X/Y bias |
| MPU6886 | Offline per-run plateau bias | MPU6886_017 | -0.0000 | 0.0000 | 0.0000 | 0.0563 | 0.0415 | 0.0318 | n/a | 0 | 0 | 0 | BOUND only |

## Interpretation

- `tel_148` shows the actual BMI270 signal after the current pipeline/ZARU path: the final gyro input is centered near zero, with about 0.006 dps standard deviation and clean logging.
- `MPU6886_014 -> MPU6886_017` shows that a fixed calibration is not acceptable on X/Y for this device: the residual bias remains about 1.293 / 1.829 dps.
- The per-run plateau replay proves the MPU6886 can be re-centered if a runtime bias estimator is available, but this is a static bound, not a demonstrated firmware ESKF result.
- The TCO result from `tel_148` is excluded from the verdict because that run had strong ambient thermal excursion.
