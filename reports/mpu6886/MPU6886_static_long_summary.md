# MPU6886 static long-run summary

Current MPU6886 bench mode: high-bandwidth FIFO source decimated to 50 Hz, no firmware bias correction, no ZARU, no pipeline filtering.

| Test | Orientation | Plateau min | Temp mean C | Temp span C | Gyro mean X/Y/Z dps | Gyro std X/Y/Z dps | Gyro slope X/Y/Z dps/h | Diagnostics |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| MPU6886_001 | +Z | 99.8 | 37.70 | 0.695 | -5.092/-2.798/-0.792 | 0.1299/0.0893/0.0578 | +0.198/+0.110/+0.001 | OK |
| MPU6886_002 | -X | 101.0 | 37.89 | 0.695 | -3.732/-1.710/-0.622 | 0.0905/0.0732/0.0586 | -0.075/-0.041/-0.019 | OK |
| MPU6886_003 | +X | 52.7 | 38.50 | 0.688 | -4.042/-2.936/-0.415 | 0.1012/0.0854/0.0576 | +0.031/+0.037/-0.000 | OK |
| MPU6886_007 | -Z | 63.5 | 37.35 | 0.695 | -3.043/-1.750/-0.544 | 0.0830/0.0719/0.0588 | +0.080/+0.084/+0.013 | OK |
| MPU6886_010 | -Y | 93.2 | 37.14 | 0.670 | -2.517/-1.547/-0.554 | 0.1363/0.1067/0.0667 | -0.101/+0.040/+0.011 | OK |
| MPU6886_011 | +Y | 107.7 | 37.43 | 0.695 | -4.384/-3.216/-0.539 | 0.1836/0.2002/0.0634 | +0.164/+0.269/-0.004 | OK |

## Reading

- All included long logs are structurally clean: no CRC errors, resync, sequence gaps, timestamp drop estimate, FIFO overrun, stale samples, or SD drops.
- Orientation coverage: +Z, -X, +X, -Z, -Y, +Y.
- Orientation is inferred from the dominant plateau accelerometer axis.
- This is high-bandwidth/raw-path evidence. The fair operating-path comparison still needs MPU6886 with DLPF/ODR configured near the BMI270 LPF20/22 test conditions.
