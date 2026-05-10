# MPU6886 repeat comparison: +Z face

Scope: compare repeat runs `MPU6886_012` and `MPU6886_013` against earlier same-face `MPU6886_001`, using the same plateau detector as the six-face raw/high-bandwidth study.

| Test | Orientation | Plateau min | Temp C | Acc mean X/Y/Z g | Gyro mean X/Y/Z dps | Gyro std X/Y/Z dps | Gyro slope X/Y/Z dps/h |
|---|---:|---:|---:|---:|---:|---:|---:|
| MPU6886_001 | +Z | 99.8 | 37.70 | +0.0339/-0.0174/+1.0097 | -5.092/-2.798/-0.792 | 0.1299/0.0893/0.0578 | +0.198/+0.110/+0.001 |
| MPU6886_012 | +Z | 85.2 | 39.14 | +0.0326/-0.0120/+1.0113 | -2.849/-1.470/-0.547 | 0.0776/0.0925/0.0586 | -0.019/+0.127/+0.010 |
| MPU6886_013 | +Z | 45.2 | 37.45 | +0.0321/-0.0110/+1.0105 | -2.980/-2.318/-0.473 | 0.1233/0.1043/0.0589 | +0.039/+0.126/+0.018 |

## Bias deltas

| Delta | X dps | Y dps | Z dps |
|---|---:|---:|---:|
| MPU6886_012 - MPU6886_001 | +2.243 | +1.327 | +0.245 |
| MPU6886_013 - MPU6886_001 | +2.112 | +0.479 | +0.318 |
| MPU6886_013 - MPU6886_012 | -0.130 | -0.848 | +0.074 |

## Notes

- Repeat orientation check: +Z, +Z, +Z. All three are the same +Z face.
- Repeat pair `013-012` changes gyro bias by X -0.130 dps, Y -0.848 dps, Z +0.074 dps.
- Accel mean change `013-012` is X -0.0005 g, Y +0.0009 g, Z -0.0008 g, so the physical pose is close but not mathematically identical.
- These deltas are too large on X/Y to be explained only by white noise; they include power-cycle/startup bias and/or small pose/G-sensitivity effects.
- Z remains much more repeatable than X/Y, consistent with the six-face study.
