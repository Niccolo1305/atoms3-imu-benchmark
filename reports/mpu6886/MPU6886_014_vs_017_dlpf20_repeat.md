# MPU6886 DLPF20 repeat check: 014 vs 017

Reference: `MPU6886_014` face +Z, repeat: `MPU6886_017` face +Z. Same face: True.

| Metric | X | Y | Z |
|---|---:|---:|---:|
| 014 gyro mean (dps) | -3.97329 | -2.92446 | -0.50609 |
| 017 gyro mean (dps) | -2.67983 | -1.09530 | -0.50534 |
| Delta 017-014 gyro mean (dps) | +1.29346 | +1.82916 | +0.00075 |
| 014 gyro std (dps) | 0.06057 | 0.03946 | 0.03147 |
| 017 gyro std (dps) | 0.05626 | 0.04148 | 0.03177 |
| Delta accel mean (g) | -0.00063 | +0.00162 | -0.00014 |

## Reading

- This is a valid same-face repeatability check.
- Temperature mean delta: -0.90 C.
- Large gyro mean deltas with small accel pose deltas indicate non-repeatable startup bias rather than orientation error.
- The 017 full 30 min analysis window is thermally wider than the normal 0.70 C plateau target, but stricter 10-20 min subwindows with only 0.13-0.27 C span still give about `-2.67 / -1.11 / -0.50 dps`, so the X/Y bias jump remains.
