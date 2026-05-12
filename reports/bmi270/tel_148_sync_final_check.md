# BMI270 sync final check: tel_148

Source: `tel_148.bin`, firmware `v1.8.2-atoms3r`, record size 256 B.

The input file is 128 MiB and contains a preallocated empty tail. The converter
ignored 41,504,512 empty bytes and decoded a logical payload of 92,713,216 B:
362,160 telemetry rows.

## Timing / Logging

| Metric | tel_123 | tel_148 |
|---|---:|---:|
| Validator timing status | FAIL | PASS |
| Rows | 357,779 | 362,160 |
| Duration | 7156.63 s | 7243.16 s |
| Median dt | 20.003 ms | 20.004 ms |
| Mean dt | 20.003 ms | 20.000 ms |
| dt min | 7.084 ms | 2.057 ms |
| dt max | 519.911 ms | 21.677 ms |
| Timestamp gap events | 3 | 0 |
| Estimated dropped samples | 54 | 0 |
| Sequence gaps | 3 | 0 |
| Sequence drop estimate | 54 | 0 |
| FIFO overrun | 0 | 0 |
| SD records dropped | 0 | 0 |
| SD partial writes | 0 | 0 |
| SD stalls | 3 | 0 |
| SD reopens | 3 | 0 |
| FIFO backlog max | 34 | 34 |

## Sensor Plateau

| Metric | tel_148 |
|---|---:|
| Plateau | 2924.42-3625.60 s |
| Plateau duration | 11.69 min |
| Plateau temp mean | 36.69 C |
| Orientation | +Z |

| Axis | Gyro mean dps | Gyro std dps | Rate noise density dps/sqrtHz | Acc mean g | Acc std mg |
|---|---:|---:|---:|---:|---:|
| X | +0.12617 | 0.03368 | 0.00740 | +0.02693 | 0.554 |
| Y | +0.00435 | 0.04371 | 0.00881 | +0.00253 | 0.552 |
| Z | +0.64258 | 0.03424 | 0.00781 | +1.00754 | 0.669 |

## Reading

- The new SD write architecture closes the previous sync/logging failure in
  this run: no timestamp gaps, no sequence gaps, no estimated drops.
- The previous `tel_123` failures were real sequence gaps; `tel_148` removes
  them while keeping FIFO overrun at zero.
- Sensor noise remains in the expected BMI270 ODR50/LPF20 range.
- The validator reports gyro X TCO FAIL for this run, but the selected plateau
  is short and this test was intended primarily as a logging/sync confirmation.
  It does not change the prior sensor-characterization conclusion.
