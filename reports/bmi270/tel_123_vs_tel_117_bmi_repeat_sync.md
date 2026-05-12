# BMI270 repeat + sync check: tel_117 vs tel_123

| Metric | tel_117 | tel_123 | Delta / Read |
|---|---:|---:|---|
| Duration h | 1.987 | 1.988 | +0.00142735 |
| Plateau min | 50.04 | 36.52 | -13.5207 |
| Plateau temp C | 34.870 | 36.806 | +1.93661 |
| Timing status | FAIL | FAIL |  |
| Estimated dropped samples | 89 | 54 | -35 |
| Timing outliers | 7 | 4 | -3 |
| dt max s | 0.320228 | 0.519911 | +0.199683 |
| jitter p95 us | 292.000 | 304.000 | +12 |
| FIFO overrun | 0 | 0 | +0 |
| FIFO backlog max | 21.0 | 34.0 | +13 |
| IMU fresh rate | 0.998604 | 0.998569 | -3.51961e-05 |

## Gap Events

| Test | Gap events | Drop estimate | Sequence gaps | Events |
|---|---:|---:|---:|---|
| tel_117 | 6 | 89 | n/a | row 6894 dt 0.300s; row 14894 dt 0.320s; row 45788 dt 0.320s; row 62512 dt 0.320s; row 112954 dt 0.320s; row 294986 dt 0.320s |
| tel_123 | 3 | 54 | 3 | row 38862 dt 0.300s seq 38862->38877; row 65352 dt 0.520s seq 65366->65392; row 159278 dt 0.320s seq 159317->159333 |

## Gyro Plateau

| Axis | Mean 117 | Mean 123 | Delta mean | Std 117 | Std 123 | Rate noise density 117 | Rate noise density 123 | PSD 117 | PSD 123 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| X | +0.146718 | +0.207995 | +0.061277 | 0.034616 | 0.034732 | 0.007560 | 0.007715 | 0.007343 | 0.007338 |
| Y | +0.018442 | -0.007407 | -0.025849 | 0.036237 | 0.035378 | 0.008035 | 0.007996 | 0.007551 | 0.007525 |
| Z | +0.558032 | +0.491425 | -0.066606 | 0.033520 | 0.034704 | 0.007216 | 0.007411 | 0.007068 | 0.007001 |

## Accel Plateau

| Axis | Mean 117 | Mean 123 | Delta mean | Std 117 mg | Std 123 mg |
|---|---:|---:|---:|---:|---:|
| X | +0.020535 | -0.000786 | -0.021321 | 0.553 | 0.552 |
| Y | +0.006399 | -0.000021 | -0.006420 | 0.553 | 0.557 |
| Z | +1.008179 | +1.008097 | -0.000083 | 0.665 | 0.669 |

## Pipeline/ZARU Columns

### tel_117
| Column | Mean | Std | Min | Max |
|---|---:|---:|---:|---:|
| `zaru_flags` | +0.99977350 | 0.01504818 | +0.00000 | +1.00000 |

### tel_123
| Column | Mean | Std | Min | Max |
|---|---:|---:|---:|---:|
| `zaru_flags` | +0.99955272 | 0.02114446 | +0.00000 | +1.00000 |

## Reading

- tel_123 still fails timing quality: 54 estimated dropped samples and 4 timing outliers. It improves versus tel_117, but the sync/logging issue is not fully closed.
- In tel_123 the three timestamp gaps match three `seq` gaps, so these are real missing records in the log stream, not just validator rounding.
- Sensor FIFO health still looks good: `fifo_overrun_count = 0`; `sd_records_dropped = 0` in tel_123, so the missing records likely occur before or outside the SD queue-drop counter path.
- tel_123 repeats the +Z orientation well: accel Z differs from tel_117 by about -0.00008 g.
- Gyro bias repeatability is good enough for our purpose: X/Y/Z shifted by +0.061 / -0.026 / -0.067 dps, far smaller than MPU6886 same-face DLPF repeat on X/Y.
- Noise and rate noise density remain essentially unchanged; PSD remains WHITE on all gyro axes.
- ZARU is active about 99.95-99.98% of the plateau and final `gx/gy/gz` stay centered near zero with about 0.006 dps std.
