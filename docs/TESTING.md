# Testing

Automated tests are located in `tests/test_timeseries_resample.py` using `pytest`.

These tests cover:
- **Aggregation**: Correctness of mean, sum, min, max, first, last, and count calculations, including usage of `math.fsum`.
- **Bucketing**: Correct alignment of half-open intervals and origin handling.
- **Gap Filling**: Verification of `ffill`, `bfill`, `linear` (with interpolation limits), and `zero` methods.
- **Validation**: Error handling for `ResampleError` (e.g., `naive_datetime`, `too_many_buckets`, `invalid_value`).
- **Timezone Handling**: Enforcement of UTC requirements.

Run with:
```bash
uv run pytest
```
