# Architecture

`timeseries_resample` provides deterministic, zero-dependency time series resampling and gap filling.

## Resampling Pipeline

1. **Validation & Normalization**:
   - Inputs are verified as timezone-aware; non-UTC inputs are cast to UTC.
   - Interval step `every` is validated as positive.
   - Values must be `int` (excluding bool) or finite `float`. `ResampleError` is raised for invalid types or non-finite values.
2. **Bucketing**:
   - Half-open buckets `[b, b + every)` are aligned relative to `origin` via integer floor division: `b = origin + ((t - origin) // every) * every`.
   - If `start` or `end` are missing, defaults are the first and last non-empty buckets.
   - Bounds are checked against `max_buckets` before allocation.
3. **Aggregation**:
   - Points are grouped into buckets; `None` values are filtered out.
   - Aggregation per bucket: `mean` and `sum` use `math.fsum` for exact precision; `min` and `max` retain original values; `first` and `last` respect sorted input order; `count` returns integer counts.

## Gap Filling

- `ffill`/`bfill`: Propagates nearest non-None values.
- `linear`: Performs time-weighted linear interpolation `v0 + (v1 - v0) * elapsed_s / span_s`. Gaps exceeding `limit` remain `None`.
- `zero`: Replaces `None` with `0.0`.
