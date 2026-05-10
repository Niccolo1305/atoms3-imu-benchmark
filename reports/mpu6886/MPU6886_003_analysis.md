# MPU6886_003 static bench analysis

- Duration: 1.989 h, rows: 358000, fs: 50.000000 Hz
- Plateau detector: tail after 600s with remaining temp span <= 0.70 C
- Plateau: 3999.0-7160.0 s (52.7 min), temp 38.50 C, span 0.688 C
- Dominant accel axis: x (+1.00465 g)

| Metric | X | Y | Z |
|---|---:|---:|---:|
| Gyro mean plateau (dps) | -4.04184 | -2.93644 | -0.41494 |
| Gyro std plateau (dps) | 0.10119 | 0.08544 | 0.05763 |
| Gyro slope plateau (dps/h) | +0.03059 | +0.03727 | -0.00028 |
| Gyro half delta plateau (dps) | +0.01952 | +0.02308 | +0.00025 |
| Gyro residual std after mean removal (dps) | 0.10119 | 0.08544 | 0.05763 |
| Gyro residual p05/p95 after mean removal (dps) | -0.16959/+0.13559 | -0.11531/+0.12883 | -0.07334/+0.10976 |
| Acc mean plateau (g) | +1.00465 | -0.00192 | -0.01910 |
| Acc std plateau (mg) | 1.634 | 1.573 | 1.486 |

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
- sd_flush_worst_us_final: 65001
- sd_queue_high_watermark_final: 3
- fifo_overrun_count_final: 0
- decimation_counter_counts: {'19': 5984, '20': 152050, '21': 17}
