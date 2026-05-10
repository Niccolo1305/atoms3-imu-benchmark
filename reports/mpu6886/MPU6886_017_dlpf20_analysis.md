# MPU6886_017 DLPF20/ODR50 analysis

Mode: DLPF_CFG=4 gyro 3 dB BW 20 Hz, noise BW 30.5 Hz; A_DLPF_CFG=4 accel 3 dB BW 21.2 Hz, noise BW 31.0 Hz; output/logging 50 Hz.

- Duration: 1.989 h, rows: 358000, fs: 50.000000000 Hz
- Plateau: 5361.7-7161.7 s (30.0 min), temp 36.81 C, span 0.930 C
- Orientation: +Z (z +1.01028 g)
- Diagnostics: CRC bad 0, resync 0, seq gaps 0, timestamp drop estimate 0, FIFO overrun 0, SD drops 0

| Metric | X | Y | Z |
|---|---:|---:|---:|
| Gyro mean plateau (dps) | -2.67983 | -1.09530 | -0.50534 |
| Gyro std plateau (dps) | 0.05626 | 0.04148 | 0.03177 |
| Gyro PSD floor (dps/sqrtHz) | 0.01140 | 0.00845 | 0.00650 |
| Gyro PSD slope | -0.0476 | -0.0388 | -0.0317 |
| Gyro PSD flatness | 0.9759 | 0.9741 | 0.9742 |
| Gyro PSD rating | WHITE | WHITE | WHITE |
| Gyro slope plateau (dps/h) | -0.08005 | +0.04606 | -0.01326 |
| Gyro half delta plateau (dps) | -0.02319 | +0.01170 | -0.00350 |
| Gyro residual 60s mean span (dps) | 0.03457 | 0.02791 | 0.01424 |
| Acc mean plateau (g) | +0.03329 | -0.01464 | +1.01028 |
| Acc std plateau (mg) | 0.587 | 0.577 | 0.572 |

## Reading

- This is a repeat operating-LPF MPU6886 run for bias repeatability evaluation.
- Residual-after-bias metrics subtract the plateau mean and quantify whether the gyro center remains stable at near-constant temperature.
- Logger diagnostics are clean for this run.
