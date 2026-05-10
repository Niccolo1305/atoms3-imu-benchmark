# Orientamenti statici ODR50 / LPF20 summary

| Test | Orientamento | Gravita dominante | Plateau | Gyro std XYZ (dps) | ARW XYZ (dps/sqrtHz) | ZARU attivo | Timing |
|---|---:|---:|---:|---:|---:|---:|---|
| tel_116 | usb-c-up | x +0.9967 g | 20.4 min @ 34.8 C | 0.0341, 0.0351, 0.0336 | 0.0074, 0.0078, 0.0076 | 99.96% | FAIL, drops 29 |
| tel_117 | su | z +1.0082 g | 50.0 min @ 34.9 C | 0.0346, 0.0362, 0.0335 | 0.0076, 0.0080, 0.0072 | 99.98% | FAIL, drops 89 |
| tel_118 | destra | y -1.0127 g | 17.7 min @ 35.6 C | 0.0348, 0.0353, 0.0333 | 0.0079, 0.0078, 0.0073 | 99.87% | FAIL, drops 129 |

## Lettura sintetica

- I tre log ODR50 coprono tre assi gravita indipendenti: +X (`usb-c-up`), +Z (`su`) e -Y (`destra`).
- Il rumore gyro FIFO filtrato resta molto basso e coerente: circa 0.033-0.036 dps RMS per asse sul plateau, con ARW circa 0.007-0.008 dps/sqrtHz.
- La PSD del gyro e classificata WHITE su tutti gli assi e tutti i test ODR50.
- ZARU e attivo quasi sempre sul plateau e porta gli output finali `gx/gy/gz` a media circa zero con std circa 0.006 dps.
- Resta il problema timing/logging: tutti i log ODR50 hanno timing FAIL con drop stimati, ma `fifo_overrun_count` resta 0.

## File generati

- `reports/bmi270/orientamenti_statici_odr50_summary.csv`
- `reports/bmi270/orientamenti_statici_odr50_summary.md`
