# MPU6886_011 static bench analysis

- Duration: 1.989 h, rows: 358000, fs: 50.000000 Hz
- Plateau detector: tail after 600s with remaining temp span <= 0.70 C
- Plateau: 695.8-7160.0 s (107.7 min), temp 37.43 C, span 0.695 C
- Dominant accel axis: y (+0.99352 g)

| Metric | X | Y | Z |
|---|---:|---:|---:|
| Gyro mean plateau (dps) | -4.38393 | -3.21647 | -0.53867 |
| Gyro std plateau (dps) | 0.18361 | 0.20019 | 0.06335 |
| Gyro slope plateau (dps/h) | +0.16406 | +0.26856 | -0.00425 |
| Gyro half delta plateau (dps) | +0.15108 | +0.23434 | -0.00216 |
| Gyro residual std after mean removal (dps) | 0.18361 | 0.20019 | 0.06335 |
| Gyro residual p05/p95 after mean removal (dps) | -0.31578/+0.29457 | -0.32357/+0.28678 | -0.07168/+0.11142 |
| Acc mean plateau (g) | +0.00287 | +0.99352 | +0.05423 |
| Acc std plateau (mg) | 2.055 | 1.577 | 1.719 |

## Diagnostics
- crc_all_ok: True
- records_crc_bad: 0
- resync_count: 0
- seq_gaps: 0
- timestamp_gap_drop_estimate: 0
- sample_fresh_false: 0
- fifo_overrun_records: 0
- sd_records_dropped_final: 0
- read_error_count_final: 0
- sd_partial_write_count_final: 0
- sd_stall_count_final: 0
- sd_reopen_count_final: 0
- sd_flush_worst_us_final: 52998
- sd_queue_high_watermark_final: 2
- fifo_overrun_count_final: 0
- decimation_counter_counts: {'19': 12064, '20': 311099, '21': 46}
