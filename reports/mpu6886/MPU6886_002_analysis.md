# MPU6886_002 static bench analysis

- Duration: 1.989 h, rows: 358000, fs: 50.000000 Hz
- Plateau detector: tail after 600s with remaining temp span <= 0.70 C
- Plateau: 1098.9-7160.0 s (101.0 min), temp 37.89 C, span 0.695 C
- Dominant accel axis: x (-0.99589 g)

| Metric | X | Y | Z |
|---|---:|---:|---:|
| Gyro mean plateau (dps) | -3.73159 | -1.71041 | -0.62247 |
| Gyro std plateau (dps) | 0.09053 | 0.07319 | 0.05858 |
| Gyro slope plateau (dps/h) | -0.07503 | -0.04099 | -0.01907 |
| Gyro half delta plateau (dps) | -0.06141 | -0.03383 | -0.01314 |
| Gyro residual std after mean removal (dps) | 0.09053 | 0.07319 | 0.05858 |
| Gyro residual p05/p95 after mean removal (dps) | -0.17466/+0.13051 | -0.12064/+0.12350 | -0.10996/+0.07315 |
| Acc mean plateau (g) | -0.99589 | -0.00703 | +0.06826 |
| Acc std plateau (mg) | 1.681 | 1.574 | 1.494 |

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
- sd_flush_worst_us_final: 50433
- sd_queue_high_watermark_final: 2
- fifo_overrun_count_final: 0
- decimation_counter_counts: {'19': 11371, '20': 291652, '21': 30}
