# MPU6886 DLPF20/ODR50 operating summary

Mode: gyro DLPF_CFG=4, 3 dB BW 20 Hz, noise BW 30.5 Hz; accel A_DLPF_CFG=4, 3 dB BW 21.2 Hz, noise BW 31.0 Hz; output/logging 50 Hz.

| Test | Face | Plateau min | Temp C | Gyro mean X/Y/Z dps | Gyro std X/Y/Z dps | PSD floor X/Y/Z dps/sqrtHz | Residual 60s span X/Y/Z dps | Acc std X/Y/Z mg | Diagnostics |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| MPU6886_014 | +Z | 60.7 | 37.71 | -3.973 / -2.924 / -0.506 | 0.0606 / 0.0395 / 0.0315 | 0.0126 / 0.0080 / 0.0060 | 0.0350 / 0.0374 / 0.0436 | 0.610 / 0.608 / 0.593 | OK |
| MPU6886_015 | +X | 99.3 | 37.91 | -3.786 / -3.065 / -0.680 | 0.0846 / 0.0588 / 0.0297 | 0.0121 / 0.0105 / 0.0059 | 0.1690 / 0.1102 / 0.0359 | 0.623 / 0.577 / 0.562 | OK |
| MPU6886_016 | -Y | 43.1 | 36.65 | -3.500 / -1.968 / -0.785 | 0.0590 / 0.0435 / 0.0307 | 0.0113 / 0.0090 / 0.0062 | 0.0873 / 0.0299 / 0.0183 | 0.606 / 0.575 / 0.733 | OK |

## Aggregate

### Gyro std mean (dps)
| Axis | Mean | Min | Max |
|---|---:|---:|---:|
| X | 0.06805 | 0.05897 | 0.08462 |
| Y | 0.04726 | 0.03946 | 0.05880 |
| Z | 0.03064 | 0.02970 | 0.03147 |

### Gyro PSD floor mean (dps/sqrtHz)
| Axis | Mean | Min | Max |
|---|---:|---:|---:|
| X | 0.01200 | 0.01129 | 0.01260 |
| Y | 0.00917 | 0.00797 | 0.01050 |
| Z | 0.00603 | 0.00588 | 0.00624 |

### Accel std mean (mg)
| Axis | Mean | Min | Max |
|---|---:|---:|---:|
| X | 0.61289 | 0.60551 | 0.62276 |
| Y | 0.58662 | 0.57501 | 0.60762 |
| Z | 0.62907 | 0.56160 | 0.73287 |

### Gyro residual 60s span mean (dps)
| Axis | Mean | Min | Max |
|---|---:|---:|---:|
| X | 0.09711 | 0.03503 | 0.16899 |
| Y | 0.05915 | 0.02987 | 0.11023 |
| Z | 0.03263 | 0.01833 | 0.04362 |

## Same-Face Repeat: +Z 014 vs 017

| Metric | X | Y | Z |
|---|---:|---:|---:|
| 014 gyro mean (dps) | -3.97329 | -2.92446 | -0.50609 |
| 017 gyro mean (dps) | -2.67983 | -1.09530 | -0.50534 |
| Delta 017-014 (dps) | +1.29346 | +1.82916 | +0.00075 |
| Acc mean delta 017-014 (g) | -0.00063 | +0.00162 | -0.00014 |

The repeat is physically the same +Z face. The accelerometer mean changed by
only about 0.0016 g worst-axis, while gyro X/Y bias shifted by about
1.29 / 1.83 dps. Stricter 10-20 min subwindows inside 017 with 0.13-0.27 C
temperature span still give about `-2.67 / -1.11 / -0.50 dps`, so the result is
not explained by the wider 30 min thermal window. This confirms that MPU6886
X/Y startup bias is not repeatable in the filtered operating path either.
