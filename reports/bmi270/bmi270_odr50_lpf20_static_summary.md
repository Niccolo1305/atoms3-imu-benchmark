# BMI270 ODR50 / LPF20 Static Summary

| Test | Orientation | Dominant gravity | Plateau | Gyro std XYZ (dps) | Rate noise density XYZ (dps/sqrtHz) | ZARU active | Timing |
|---|---:|---:|---:|---:|---:|---:|---|
| tel_116 | usb-c-up | x +0.9967 g | 20.4 min @ 34.8 C | 0.0341, 0.0351, 0.0336 | 0.0074, 0.0078, 0.0076 | 99.96% | FAIL, drops 29 |
| tel_117 | su | z +1.0082 g | 50.0 min @ 34.9 C | 0.0346, 0.0362, 0.0335 | 0.0076, 0.0080, 0.0072 | 99.98% | FAIL, drops 89 |
| tel_118 | destra | y -1.0127 g | 17.7 min @ 35.6 C | 0.0348, 0.0353, 0.0333 | 0.0079, 0.0078, 0.0073 | 99.87% | FAIL, drops 129 |

## Summary Read

- The three ODR50 logs cover three independent gravity axes: +X (`usb-c-up`), +Z (`su`), and -Y (`destra`).
- Filtered FIFO gyro noise is low and consistent: about 0.033-0.036 dps RMS per axis inside the selected plateau, with rate noise density around 0.007-0.008 dps/sqrtHz.
- Gyro PSD is classified as WHITE on every axis in every ODR50 test.
- ZARU is active for almost the entire plateau and brings the final `gx/gy/gz` outputs near zero mean with about 0.006 dps standard deviation.
- Timing/logging remains the caveat for these ODR50 characterization logs: all three have timing FAIL with estimated drops, while `fifo_overrun_count` remains 0. The later `tel_148` run is used as the clean logging-path confirmation.

## Generated Files

- `reports/bmi270/orientamenti_statici_odr50_summary.csv`
- `reports/bmi270/bmi270_odr50_lpf20_static_summary.md`
