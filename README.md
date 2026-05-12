# AtomS3 vs AtomS3R IMU Benchmark

Public technical evidence package for comparing M5Stack AtomS3 / MPU6886 and
AtomS3R / BMI270 + BMM150 as IMU sources for a low-rate vehicle sensor-fusion
pipeline.

This repository is intentionally scoped to reproducible summaries, compact
artifacts, analysis scripts, and the dedicated MPU6886 static bench firmware.
Raw `.BIN` and large raw `.csv` logs are not committed because some vehicle
logs may contain GPS-derived fields.

## Main Results

- AtomS3R/BMI270 is the preferred IMU path for the tested firmware pipeline.
- The main BMI270 sensor characterization comes from stronger ODR50/LPF static
  plateau logs such as `tel_117`.
- The clean BMI270 confirmation run `tel_148` is used as a logging-path
  validation: zero sequence gaps, zero estimated drops, and zero FIFO overrun.
- BMI270 final firmware gyro output after pipeline/ZARU is about
  `0.0068 / 0.0058 / 0.0061 dps` standard deviation on X/Y/Z.
- MPU6886 DLPF20 same-face replay shows fixed-bias failure on X/Y:
  applying the `MPU6886_014` +Z bias to `MPU6886_017` leaves about
  `+1.293 / +1.829 dps` residual X/Y bias.
- MPU6886 can be re-centered by oracle/static bias subtraction, but that is a
  sensor-only static bound, not a demonstrated runtime ESKF/ZARU output.

The conclusion is deliberately scoped: these results characterize the tested
units and firmware paths, not every possible MPU6886 or BMI270 unit.

## Repository Map

```text
docs/
  AtomS3_vs_AtomS3R_Sensor_Bench_Whitepaper.md
  AtomS3_vs_AtomS3R_Public_IMU_Benchmark.md

reports/
  bmi270/       Compact BMI270 validator reports, dashboards, and summaries
  mpu6886/      Compact MPU6886 bench reports and summaries
  comparison/   Cross-sensor runtime/replay comparison artifacts
  figures/      Whitepaper figures

scripts/
  build_atom_runtime_comparison.py
  bosch_static_validator.py
  check_no_gps_leaks.py
  scrub_gps_columns.py

firmware/
  mpu6886-static-bench/

data/
  raw_private_NOT_COMMITTED/
```

## Recommended Reading Order

1. `docs/AtomS3_vs_AtomS3R_Public_IMU_Benchmark.md`
2. `docs/AtomS3_vs_AtomS3R_Sensor_Bench_Whitepaper.md`
3. `reports/bmi270/orientamenti_statici_odr50_summary.md`
4. `reports/bmi270/tel_148_bmi_clean_validation_summary.md`
5. `reports/comparison/eskf_input_quality_comparison.md`
6. `reports/comparison/mpu6886_zaru_replay_summary.md`
7. `reports/mpu6886/MPU6886_014_vs_017_dlpf20_repeat.md`

## Raw Data Policy

Raw captures are intentionally private:

- do not commit `*.bin`, `*.BIN`, `tel_*.csv`, or `MPU6886_*.csv`;
- keep raw files in `data/raw_private_NOT_COMMITTED/` when regenerating reports;
- publish only compact JSON/CSV/MD summaries, dashboards, and figures;
- run the privacy check before committing.

```powershell
python .\scripts\check_no_gps_leaks.py
```

## Regenerating The Runtime Comparison

The checked-in comparison artifacts are already generated. To regenerate them,
place these private raw CSVs in `data/raw_private_NOT_COMMITTED/`:

- `tel_148.csv`
- `MPU6886_014.csv`
- `MPU6886_017.csv`

Then run:

```powershell
python .\scripts\build_atom_runtime_comparison.py
```

Outputs are written to `reports/comparison/`.

## Firmware Bench

`firmware/mpu6886-static-bench/` contains the dedicated AtomS3 MPU6886 static
bench firmware used to collect clean FIFO logs. It is separate from the vehicle
pipeline: no GPS, no ESKF, no ZARU, no axis rotation, no calibration layer.

## License

GPL-3.0, matching the source project license.
