# MPU6886_010 static bench analysis

- Duration: 1.989 h, rows: 358000, fs: 50.000000 Hz
- Plateau detector: tail after 600s with remaining temp span <= 0.70 C
- Plateau: 1567.1-7160.0 s (93.2 min), temp 37.14 C, span 0.670 C
- Dominant accel axis: y (-1.00847 g)

| Metric | X | Y | Z |
|---|---:|---:|---:|
| Gyro mean plateau (dps) | -2.51728 | -1.54669 | -0.55421 |
| Gyro std plateau (dps) | 0.13630 | 0.10674 | 0.06667 |
| Gyro slope plateau (dps/h) | -0.10136 | +0.04003 | +0.01057 |
| Gyro half delta plateau (dps) | -0.08956 | +0.02913 | +0.00608 |
| Gyro residual std after mean removal (dps) | 0.13630 | 0.10674 | 0.06667 |
| Gyro residual p05/p95 after mean removal (dps) | -0.22930/+0.19795 | -0.16229/+0.14288 | -0.11718/+0.12696 |
| Acc mean plateau (g) | +0.00757 | -1.00847 | +0.02970 |
| Acc std plateau (mg) | 2.304 | 2.084 | 4.267 |

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
- sd_flush_worst_us_final: 50314
- sd_queue_high_watermark_final: 2
- fifo_overrun_count_final: 0
- decimation_counter_counts: {'19': 10387, '20': 269233, '21': 25}
