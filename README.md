# timeseries-resample

Resample irregular time series into fixed UTC buckets with seven aggregations and fill gaps by forward, backward, linear time-weighted or zero fill with limits.

## Problem
Sensor readings, metrics, and price data often arrive at irregular intervals. To compute rates or aggregate data, this input must be aligned to a fixed time grid. While heavy libraries like `pandas` solve this, they introduce significant dependencies that are often excessive for lightweight services or CLIs. Naive implementations frequently fail on edge cases involving UTC alignment, empty bucket handling, and floating-point summation errors.

## Installation

```bash
pip install timeseries-resample
```

## Usage

```python
from datetime import datetime, timedelta, timezone
from timeseries_resample import resample, fill

points = [(datetime(2026, 11, 6, 0, 0, 10, tzinfo=timezone.utc), 1.0)]
grid = resample(points, every=timedelta(minutes=1), agg="mean")
result = fill(grid, "zero")
```

## Public API Summary

- `resample(points, *, every, agg, origin=..., start=..., end=..., label='left', max_points=1000000, max_buckets=1000000)`: Aggregates points into fixed buckets. `agg` accepts 'mean', 'sum', 'min', 'max', 'first', 'last', 'count'. Raises `ResampleError` for naive datetimes, invalid aggregations, invalid intervals, invalid ranges, or limits.
- `fill(series, method, *, limit=None)`: Fills gaps in resampled series. `method` accepts 'ffill', 'bfill', 'linear', 'zero'. Raises `ResampleError` for unknown methods or invalid limits.
- `ResampleError(code, message)`: Base exception containing a machine-readable `code`.

## Why not pandas?
This utility provides zero dependencies, strictly explicit boundary rules, and exact float summations via `math.fsum`, making it more stable and predictable for CLI tools and lightweight services.

See [Security Policy](docs/SECURITY.md) for details on threat handling.
