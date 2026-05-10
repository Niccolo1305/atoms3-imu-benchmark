# MPU6886 ZARU Replay Summary

Replay type: static sensor-only bias subtraction on MPU6886 DLPF20/21.2 logs. This is not full SITL ESKF and not firmware ZARU output.

## Repeatability Anchor

| Metric | X | Y | Z |
| --- | --- | --- | --- |
| 014 -> 017 gyro mean delta dps | 1.2935 | 1.8292 | 0.0008 |
| 014 -> 017 gyro std delta dps | -0.0043 | 0.0020 | 0.0003 |

## Replay Cases

| Case | Eval run | samples | mean X | mean Y | mean Z | std X | std Y | std Z | angle p2p X | angle p2p Y | angle p2p Z | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_014_to_017 | MPU6886_017 | 89917 | 1.2935 | 1.8292 | 0.0008 | 0.0563 | 0.0415 | 0.0318 | 2326.0439 | 3289.4483 | 2.3459 | FAIL: fixed +Z calibration leaves large X/Y residual bias |
| boot_120s_017 | MPU6886_017 | 89917 | 0.6259 | 1.6589 | -0.1770 | 0.0563 | 0.0415 | 0.0318 | 1125.6189 | 2983.1833 | 318.2600 | PARTIAL: boot estimate helps only if startup window is static and thermally representative |
| oracle_017 | MPU6886_017 | 89917 | -0.0000 | 0.0000 | 0.0000 | 0.0563 | 0.0415 | 0.0318 | 10.6555 | 6.0049 | 1.6295 | BOUND: centers plateau but requires runtime bias estimation |
| oracle_014 | MPU6886_014 | 182001 | -0.0000 | -0.0000 | 0.0000 | 0.0606 | 0.0395 | 0.0315 | 16.8556 | 11.6351 | 18.4450 | BOUND: centers plateau but requires runtime bias estimation |

Fixed-bias replay fails because X/Y startup bias is not repeatable across the same +Z face. Per-run/oracle bias subtraction recenters the static plateau, so MPU6886 recovery depends on a robust runtime bias estimator and later dynamic validation.
