# Data Policy

This repository does not track raw sensor logs.

Use `raw_private_NOT_COMMITTED/` locally when you need to regenerate reports
from raw `.BIN` or `.csv` captures. That directory is ignored by git.

Public artifacts should be compact and privacy-safe:

- Markdown summaries;
- JSON report outputs;
- aggregate CSV summaries;
- dashboard PNGs;
- scripts needed to reproduce the analysis when private raw data is available.

Do not commit vehicle-format CSVs containing GPS, navigation, or fix-time
columns. If a small public sample is needed in the future, create it with
`scripts/scrub_gps_columns.py` and review it with
`scripts/check_no_gps_leaks.py` before committing.
