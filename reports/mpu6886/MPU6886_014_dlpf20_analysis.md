# MPU6886_014 DLPF20/ODR50 analysis

Mode: DLPF_CFG=4 gyro 3 dB BW 20 Hz, noise BW 30.5 Hz; A_DLPF_CFG=4 accel 3 dB BW 21.2 Hz, noise BW 31.0 Hz; output/logging 50 Hz.

- Duration: 1.989 h, rows: 358000, fs: 50.000000007 Hz
- Plateau: 3520.0-7161.6 s (60.7 min), temp 37.71 C, span 0.698 C
- Orientation: +Z (z +1.01042 g)
- Diagnostics: CRC bad 0, resync 0, seq gaps 0, timestamp drop estimate 0, FIFO overrun 0, SD drops 0

| Metric | X | Y | Z |
|---|---:|---:|---:|
| Gyro mean plateau (dps) | -3.97329 | -2.92446 | -0.50609 |
| Gyro std plateau (dps) | 0.06057 | 0.03946 | 0.03147 |
| Gyro PSD floor (dps/sqrtHz) | 0.01260 | 0.00797 | 0.00596 |
| Gyro PSD slope | -0.0885 | -0.0785 | -0.0506 |
| Gyro PSD flatness | 0.9816 | 0.9855 | 0.9862 |
| Gyro PSD rating | WHITE | WHITE | WHITE |
| Gyro slope plateau (dps/h) | -0.03402 | -0.01462 | +0.03479 |
| Gyro half delta plateau (dps) | -0.01838 | -0.00441 | +0.01464 |
| Gyro residual 60s mean span (dps) | 0.03503 | 0.03735 | 0.04362 |
| Acc mean plateau (g) | +0.03392 | -0.01626 | +1.01042 |
| Acc std plateau (mg) | 0.610 | 0.608 | 0.593 |

## Reading

- This is an operating-LPF MPU6886 run; compare it against BMI270 ODR50/LPF20, not against BMI raw/downsampled.
- Residual-after-bias metrics subtract the plateau mean and quantify whether the gyro center remains stable at near-constant temperature.
- Logger diagnostics are clean for this run.
