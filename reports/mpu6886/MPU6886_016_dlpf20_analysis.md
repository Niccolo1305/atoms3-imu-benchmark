# MPU6886_016 DLPF20/ODR50 analysis

Mode: DLPF_CFG=4 gyro 3 dB BW 20 Hz, noise BW 30.5 Hz; A_DLPF_CFG=4 accel 3 dB BW 21.2 Hz, noise BW 31.0 Hz; output/logging 50 Hz.

- Duration: 1.990 h, rows: 358250, fs: 50.000000000 Hz
- Plateau: 4577.7-7166.6 s (43.1 min), temp 36.65 C, span 0.695 C
- Orientation: -Y (y -1.00802 g)
- Diagnostics: CRC bad 0, resync 0, seq gaps 0, timestamp drop estimate 0, FIFO overrun 0, SD drops 0

| Metric | X | Y | Z |
|---|---:|---:|---:|
| Gyro mean plateau (dps) | -3.49990 | -1.96824 | -0.78521 |
| Gyro std plateau (dps) | 0.05897 | 0.04352 | 0.03074 |
| Gyro PSD floor (dps/sqrtHz) | 0.01129 | 0.00905 | 0.00624 |
| Gyro PSD slope | -0.0575 | -0.0580 | -0.0615 |
| Gyro PSD flatness | 0.9777 | 0.9811 | 0.9811 |
| Gyro PSD rating | WHITE | WHITE | WHITE |
| Gyro slope plateau (dps/h) | +0.11029 | -0.00651 | +0.01191 |
| Gyro half delta plateau (dps) | +0.03648 | -0.00128 | +0.00463 |
| Gyro residual 60s mean span (dps) | 0.08732 | 0.02987 | 0.01833 |
| Acc mean plateau (g) | -0.01334 | -1.00802 | -0.02797 |
| Acc std plateau (mg) | 0.606 | 0.575 | 0.733 |

## Reading

- This is an operating-LPF MPU6886 run; compare it against BMI270 ODR50/LPF20, not against BMI raw/downsampled.
- Residual-after-bias metrics subtract the plateau mean and quantify whether the gyro center remains stable at near-constant temperature.
- Logger diagnostics are clean for this run.
