# MPU6886_007 static bench analysis

- Duration: 1.987 h, rows: 357750, fs: 50.000000 Hz
- Plateau detector: tail after 600s with remaining temp span <= 0.70 C
- Plateau: 3342.3-7155.0 s (63.5 min), temp 37.35 C, span 0.695 C
- Dominant accel axis: z (-0.99146 g)

| Metric | X | Y | Z |
|---|---:|---:|---:|
| Gyro mean plateau (dps) | -3.04309 | -1.75030 | -0.54418 |
| Gyro std plateau (dps) | 0.08303 | 0.07190 | 0.05875 |
| Gyro slope plateau (dps/h) | +0.07997 | +0.08351 | +0.01328 |
| Gyro half delta plateau (dps) | +0.04494 | +0.04601 | +0.00970 |
| Gyro residual std after mean removal (dps) | 0.08303 | 0.07190 | 0.05875 |
| Gyro residual p05/p95 after mean removal (dps) | -0.13074/+0.11340 | -0.14179/+0.10235 | -0.06617/+0.11694 |
| Acc mean plateau (g) | -0.01980 | +0.00321 | -0.99146 |
| Acc std plateau (mg) | 1.661 | 1.570 | 1.472 |

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
- sd_flush_worst_us_final: 59046
- sd_queue_high_watermark_final: 3
- fifo_overrun_count_final: 0
- decimation_counter_counts: {'19': 7097, '20': 183517, '21': 20}
