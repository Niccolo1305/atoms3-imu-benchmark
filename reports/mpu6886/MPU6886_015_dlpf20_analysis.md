# MPU6886_015 DLPF20/ODR50 analysis

Mode: DLPF_CFG=4 gyro 3 dB BW 20 Hz, noise BW 30.5 Hz; A_DLPF_CFG=4 accel 3 dB BW 21.2 Hz, noise BW 31.0 Hz; output/logging 50 Hz.

- Duration: 1.990 h, rows: 358250, fs: 50.000000007 Hz
- Plateau: 1208.5-7166.6 s (99.3 min), temp 37.91 C, span 0.698 C
- Orientation: +X (x +1.00481 g)
- Diagnostics: CRC bad 0, resync 0, seq gaps 0, timestamp drop estimate 0, FIFO overrun 0, SD drops 0

| Metric | X | Y | Z |
|---|---:|---:|---:|
| Gyro mean plateau (dps) | -3.78614 | -3.06499 | -0.68000 |
| Gyro std plateau (dps) | 0.08462 | 0.05880 | 0.02970 |
| Gyro PSD floor (dps/sqrtHz) | 0.01212 | 0.01050 | 0.00588 |
| Gyro PSD slope | -0.0911 | -0.0867 | -0.0417 |
| Gyro PSD flatness | 0.9817 | 0.9834 | 0.9921 |
| Gyro PSD rating | WHITE | WHITE | WHITE |
| Gyro slope plateau (dps/h) | -0.12507 | -0.05344 | -0.01094 |
| Gyro half delta plateau (dps) | -0.10990 | -0.05297 | -0.00850 |
| Gyro residual 60s mean span (dps) | 0.16899 | 0.11023 | 0.03595 |
| Acc mean plateau (g) | +1.00481 | -0.00105 | -0.01586 |
| Acc std plateau (mg) | 0.623 | 0.577 | 0.562 |

## Reading

- This is an operating-LPF MPU6886 run; compare it against BMI270 ODR50/LPF20, not against BMI raw/downsampled.
- Residual-after-bias metrics subtract the plateau mean and quantify whether the gyro center remains stable at near-constant temperature.
- Logger diagnostics are clean for this run.
