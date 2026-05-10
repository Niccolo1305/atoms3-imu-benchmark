# Raw/high-bandwidth BMI270 vs MPU6886 comparison

Scope: BMI270 raw/downsampled static-orientation set versus MPU6886 FIFO high-bandwidth six-face set. This is not the operating-LPF comparison.

| Metric | BMI270 raw/downsampled | MPU6886 raw/high-bandwidth | Read |
|---|---:|---:|---|
| Gyro std avg XYZ (dps) | 0.9012 mean across axes/tests | 0.1208 / 0.1045 / 0.0605 | MPU6886 has much lower instantaneous raw gyro sample noise. |
| Gyro PSD floor / ARW approx (dps/sqrtHz) | 0.1798 PSD floor, 0.1805 ARW | 0.0212 / 0.0176 / 0.0120 PSD floor | MPU6886 raw noise floor is lower in these logs. |
| Gyro PSD whiteness | 27/27 axes WHITE | 18/18 axes WHITE | Both are predominantly white-noise limited at sample level. |
| Gyro bias envelope (dps) | X/Y small, Z around +0.53 mean in raw set | X -5.09..-2.52, Y -3.22..-1.55, Z -0.79..-0.41 | MPU6886 loses badly on raw X/Y bias magnitude. |
| Accel std avg (mg) | 3.978 | 1.830 / 1.660 / 1.991 | MPU6886 raw accel appears quieter than BMI raw; BMI ODR/LPF remains the practical path. |

## Interpretation

- Raw sample noise alone favors MPU6886: gyro std is roughly 0.06-0.12 dps on MPU6886 versus about 0.90 dps on BMI270 raw/downsampled.
- Spectrally, both sensors show mostly white gyro noise in these static tests; the difference is amplitude, not a narrowband interference problem.
- System quality does not follow raw noise alone: MPU6886 X/Y bias is large and same-face repeats show poor startup repeatability, while BMI270 bias is smaller/more manageable in the current pipeline.
- The operating comparison remains BMI270 LPF20/22 versus MPU6886 DLPF20/50 Hz.
