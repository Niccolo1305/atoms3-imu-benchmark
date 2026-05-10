# BMI270 conclusions validated by clean log tel_148

`tel_148` is the first long AtomS3R/BMI270 vehicle-format log in this study with clean timing and sequence diagnostics. It is therefore used here as a clean-run confirmation of the earlier BMI270 conclusions.

## Clean Logging Gate

| Check | tel_148 | Result |
|---|---:|---|
| Timing status | PASS | OK |
| Estimated dropped samples | 0 | OK |
| Sequence gaps | 0 | OK |
| FIFO overrun | 0 | OK |
| SD records dropped | 0 | OK |
| SD stalls/reopens | 0 / 0 | OK |

## Sensor Metrics Confirmed

| Metric | Previous ODR50 range/mean | tel_148 clean run | Read |
|---|---:|---:|---|
| Gyro std X/Y/Z | mean 0.03452 / 0.03554 / 0.03346 dps | 0.03368 / 0.04371 / 0.03424 dps | Same order; Y is higher in tel_148 but still small. |
| Gyro ARW X/Y/Z | mean 0.00763 / 0.00790 / 0.00737 | 0.00740 / 0.00881 / 0.00781 | Same 0.007-0.009 dps/sqrtHz class. |
| PSD whiteness | WHITE on 9/9 previous ODR50 gyro axes | WHITE / WHITE / WHITE | White-noise model still valid. |
| Gyro bias X/Y/Z | previous +0.147..+0.213 / +0.002..+0.058 / +0.542..+0.566 dps | +0.12617 / +0.00435 / +0.64258 dps | X/Y remain small; Z remains positive and must be corrected. |
| Accel std X/Y/Z | mean 0.555 / 0.653 / 0.684 mg | 0.554 / 0.552 / 0.669 mg | Same clean low-noise accel class. |
| Final gyro std X/Y/Z after ZARU | mean 0.00605 / 0.00603 / 0.00593 dps | 0.00677 / 0.00585 / 0.00609 dps | ZARU final output remains centered and quiet. |

## Pipeline / ZARU

| Column | Mean | Std | Min | Max |
|---|---:|---:|---:|---:|
| `gx (°/s)` | -0.00003036 | 0.00677225 | -0.02641 | +0.02460 |
| `gy (°/s)` | -0.00000830 | 0.00584929 | -0.02342 | +0.02589 |
| `gz (°/s)` | -0.00001015 | 0.00609191 | -0.02217 | +0.02336 |
| `zaru_flags` | +0.99409567 | 0.07661357 | +0.00000 | +1.00000 |
| `pipe_body_gx (°/s)` | -0.10499521 | 0.04340937 | -0.23330 | +0.01188 |
| `pipe_body_gy (°/s)` | -0.05850931 | 0.03361956 | -0.17732 | +0.06840 |
| `pipe_body_gz (°/s)` | -0.12010781 | 0.03429395 | -0.21687 | -0.02681 |
| `tbias_gz (°/s)` | -0.12010033 | 0.00604961 | -0.14138 | -0.09895 |

## Conclusion

- `tel_148` validates the earlier BMI270 sensor conclusions without the previous logging-gap caveat.
- ODR50/LPF20 gyro noise, ARW, PSD whiteness, accel noise, and ZARU behavior match the previous characterization.
- BMI270 X/Y gyro bias remains small and repeatable enough for the current correction strategy; Z offset remains positive and must continue to be corrected by boot/static bias and ZARU.
- The TCO failure in this run is not used as a sensor verdict because the environment had significant temperature movement and the validator selected only a short 11.7 min plateau.
