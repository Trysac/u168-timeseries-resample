"""Resample irregular time series into fixed UTC buckets and fill gaps."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

__all__ = [
    "Agg",
    "FillMethod",
    "ResampleError",
    "__version__",
    "fill",
    "resample",
]

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

Agg = Literal["mean", "sum", "min", "max", "first", "last", "count"]
FillMethod = Literal["ffill", "bfill", "linear", "zero"]
ErrorCode = Literal[
    "naive_datetime",
    "invalid_value",
    "invalid_interval",
    "invalid_range",
    "too_many_buckets",
    "too_many_points",
    "invalid_limit",
    "invalid_agg",
]

VALID_AGGS: frozenset[str] = frozenset({"mean", "sum", "min", "max", "first", "last", "count"})
VALID_FILL_METHODS: frozenset[str] = frozenset({"ffill", "bfill", "linear", "zero"})


class ResampleError(Exception):
    """Base exception raised by timeseries_resample with a stable machine-readable error code."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        # Never include secrets or > 200 chars in message
        safe_message = message[:200]
        super().__init__(safe_message)
        self.code: ErrorCode = code


def _ensure_utc(dt: datetime, name: str = "datetime") -> datetime:
    """Validate that dt is aware and convert it to UTC."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ResampleError(
            "naive_datetime",
            f"{name} must be timezone-aware",
        )
    return dt.astimezone(timezone.utc)


def _floor_bucket(dt_utc: datetime, origin_utc: datetime, step_us: int) -> datetime:
    """Compute half-open bucket start b = origin + k * every using floor division."""
    diff_us = int((dt_utc - origin_utc).total_seconds() * 1_000_000)
    k = diff_us // step_us
    return origin_utc + timedelta(microseconds=k * step_us)


def _validate_numeric_value(val: Any) -> float | int | None:
    """Ensure value is None, int (excluding bool), or a finite float."""
    if val is None:
        return None
    # Note: in Python, isinstance(True, int) is True, so explicitly disallow bool
    if isinstance(val, bool):
        raise ResampleError(
            "invalid_value",
            f"Value must be int or finite float, got bool: {val}",
        )
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            raise ResampleError(
                "invalid_value",
                f"Value must be finite, got: {val}",
            )
        return val
    raise ResampleError(
        "invalid_value",
        f"Value must be int, finite float, or None, got: {type(val).__name__}",
    )


def resample(
    points: Iterable[tuple[datetime, float | int | None]],
    *,
    every: timedelta,
    agg: Agg,
    origin: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc),
    start: datetime | None = None,
    end: datetime | None = None,
    label: Literal["left", "right"] = "left",
    max_points: int = 1_000_000,
    max_buckets: int = 1_000_000,
) -> list[tuple[datetime, float | int | None]]:
    """Resample irregular time series into fixed UTC buckets with the given aggregation."""
    if agg not in VALID_AGGS:
        raise ResampleError("invalid_agg", f"Unknown aggregation: {agg}")
    if label not in ("left", "right"):
        raise ResampleError("invalid_interval", f"Invalid label: {label}")

    step_us = int(every.total_seconds() * 1_000_000)
    if step_us <= 0:
        raise ResampleError(
            "invalid_interval",
            f"Interval 'every' must be positive, got {every}",
        )

    origin_utc = _ensure_utc(origin, "origin")

    start_utc = _ensure_utc(start, "start") if start is not None else None
    end_utc = _ensure_utc(end, "end") if end is not None else None

    if start_utc is not None and end_utc is not None and end_utc <= start_utc:
        raise ResampleError(
            "invalid_range",
            f"end ({end_utc.isoformat()}) must be greater than start ({start_utc.isoformat()})",
        )

    # Ingest and validate points up to max_points
    collected_points: list[tuple[datetime, float | int | None]] = []
    for pt in points:
        if len(collected_points) >= max_points:
            raise ResampleError(
                "too_many_points",
                f"Points exceeded maximum of {max_points}",
            )
        pt_dt, pt_val = pt
        dt_utc = _ensure_utc(pt_dt, "point datetime")
        val = _validate_numeric_value(pt_val)
        collected_points.append((dt_utc, val))

    # Stable sort by time order. Ties in time preserve input order.
    collected_points.sort(key=lambda x: x[0])

    # Determine bucket bounds
    b_start: datetime | None = None
    b_end: datetime | None = None

    if start_utc is not None:
        b_start = _floor_bucket(start_utc, origin_utc, step_us)

    if end_utc is not None:
        # end is exclusive, aligned up. If end_utc falls on exact boundary, it is that boundary.
        # b_end is the bucket upper boundary (exclusive).
        b_end_floor = _floor_bucket(end_utc, origin_utc, step_us)
        if b_end_floor == end_utc:
            b_end = b_end_floor
        else:
            b_end = b_end_floor + timedelta(microseconds=step_us)

    if collected_points:
        first_pt_dt = collected_points[0][0]
        last_pt_dt = collected_points[-1][0]
        first_pt_bucket = _floor_bucket(first_pt_dt, origin_utc, step_us)
        last_pt_bucket = _floor_bucket(last_pt_dt, origin_utc, step_us)

        if b_start is None:
            b_start = first_pt_bucket
        if b_end is None:
            # The last non-empty bucket ends at last_pt_bucket + step_us
            b_end = last_pt_bucket + timedelta(microseconds=step_us)

    if b_start is None or b_end is None:
        # No points and start/end not fully defined
        return []

    if b_end <= b_start:
        return []

    # Calculate total buckets
    total_span_us = int((b_end - b_start).total_seconds() * 1_000_000)
    num_buckets = total_span_us // step_us
    if total_span_us % step_us != 0:
        num_buckets += 1

    if num_buckets > max_buckets:
        raise ResampleError(
            "too_many_buckets",
            f"Requested range requires {num_buckets} buckets, exceeding max_buckets {max_buckets}",
        )

    # Group points into buckets
    bucket_values: dict[int, list[float | int]] = {i: [] for i in range(num_buckets)}

    for pt_dt, pt_val in collected_points:
        if pt_val is None:
            continue
        diff_us = int((pt_dt - b_start).total_seconds() * 1_000_000)
        idx = diff_us // step_us
        if 0 <= idx < num_buckets:
            bucket_values[idx].append(pt_val)

    result: list[tuple[datetime, float | int | None]] = []
    for i in range(num_buckets):
        bucket_left = b_start + timedelta(microseconds=i * step_us)
        lbl = bucket_left if label == "left" else bucket_left + timedelta(microseconds=step_us)
        vals = bucket_values[i]

        if agg == "count":
            result.append((lbl, len(vals)))
            continue

        if not vals:
            result.append((lbl, None))
            continue

        if agg == "sum":
            result.append((lbl, math.fsum(vals)))
        elif agg == "mean":
            result.append((lbl, math.fsum(vals) / len(vals)))
        elif agg == "min":
            result.append((lbl, min(vals)))
        elif agg == "max":
            result.append((lbl, max(vals)))
        elif agg == "first":
            result.append((lbl, vals[0]))
        elif agg == "last":
            result.append((lbl, vals[-1]))

    return result


def fill(
    series: Sequence[tuple[datetime, float | None]],
    method: FillMethod,
    *,
    limit: int | None = None,
) -> list[tuple[datetime, float | None]]:
    """Fill missing (None) values in a resampled series."""
    if method not in VALID_FILL_METHODS:
        raise ResampleError("invalid_agg", f"Unknown fill method: {method}")

    if limit is not None and limit < 1:
        raise ResampleError(
            "invalid_limit",
            f"limit must be >= 1, got {limit}",
        )

    if not series:
        return []

    n = len(series)
    times = [item[0] for item in series]
    values = [item[1] for item in series]

    if method == "zero":
        zero_vals: list[float | None] = [0.0 if v is None else float(v) for v in values]
        return list(zip(times, zero_vals, strict=True))

    res_vals: list[float | None] = list(values)

    if method == "ffill":
        last_val: float | None = None
        consecutive_filled = 0
        for i in range(n):
            val = values[i]
            if val is not None:
                last_val = float(val)
                consecutive_filled = 0
            else:
                if last_val is not None and (limit is None or consecutive_filled < limit):
                    res_vals[i] = last_val
                    consecutive_filled += 1
        return list(zip(times, res_vals, strict=True))

    if method == "bfill":
        next_val: float | None = None
        consecutive_filled = 0
        for i in range(n - 1, -1, -1):
            val = values[i]
            if val is not None:
                next_val = float(val)
                consecutive_filled = 0
            else:
                if next_val is not None and (limit is None or consecutive_filled < limit):
                    res_vals[i] = next_val
                    consecutive_filled += 1
        return list(zip(times, res_vals, strict=True))

    # method == 'linear'
    i = 0
    while i < n:
        curr = res_vals[i]
        if curr is not None:
            res_vals[i] = float(curr)
            i += 1
            continue

        # Found start of None gap
        gap_start = i
        while i < n and res_vals[i] is None:
            i += 1
        gap_end = i  # exclusive

        # Determine left neighbour
        left_idx = gap_start - 1
        right_idx = gap_end

        # Leading or trailing None stays None under linear
        if left_idx < 0 or right_idx >= n:
            continue

        gap_len = gap_end - gap_start
        if limit is not None and gap_len > limit:
            # for 'linear' a gap longer than limit stays None entirely
            continue

        v0_raw = values[left_idx]
        v1_raw = values[right_idx]
        if v0_raw is None or v1_raw is None:
            continue
        v0 = float(v0_raw)
        v1 = float(v1_raw)
        t0 = times[left_idx]
        t1 = times[right_idx]
        span_s = (t1 - t0).total_seconds()

        for k in range(gap_start, gap_end):
            tk = times[k]
            elapsed_s = (tk - t0).total_seconds()
            # linear formula: v0 + (v1 - v0) * elapsed_s / span_s
            res_vals[k] = v0 + (v1 - v0) * elapsed_s / span_s

    return list(zip(times, res_vals, strict=True))
