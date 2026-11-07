"""Unit tests for timeseries_resample."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from timeseries_resample import (
    ResampleError,
    fill,
    resample,
)


def t(time_str: str) -> datetime:
    """Acceptance helper for datetime(2026, 11, 6, HH, MM, SS, tzinfo=timezone.utc)."""
    parts = [int(p) for p in time_str.split(":")]
    return datetime(2026, 11, 6, parts[0], parts[1], parts[2], tzinfo=timezone.utc)


def test_acceptance_item_1() -> None:
    # resample([(t('00:00:10'), 1.0), (t('00:00:50'), 3.0), (t('00:01:30'), 5.0)], every=timedelta(minutes=1), agg='mean') on 2026-11-06 UTC returns [(datetime(2026, 11, 6, 0, 0, tzinfo=timezone.utc), 2.0), (datetime(2026, 11, 6, 0, 1, tzinfo=timezone.utc), 5.0)]
    res = resample(
        [
            (t("00:00:10"), 1.0),
            (t("00:00:50"), 3.0),
            (t("01:30"), 5.0)
            if ":" in "01:30" and "01:30".count(":") == 2
            else (t("00:01:30"), 5.0),
        ],
        every=timedelta(minutes=1),
        agg="mean",
    )
    assert res == [
        (datetime(2026, 11, 6, 0, 0, tzinfo=timezone.utc), 2.0),
        (datetime(2026, 11, 6, 0, 1, tzinfo=timezone.utc), 5.0),
    ]


def test_acceptance_item_2() -> None:
    # Points at 00:00 (1.0) and 00:03 (4.0) with every one minute give values [1.0, None, None, 4.0] for agg 'sum' and [1, 0, 0, 1] for agg 'count'
    pts = [(t("00:00:00"), 1.0), (t("00:03:00"), 4.0)]
    res_sum = resample(pts, every=timedelta(minutes=1), agg="sum")
    assert [val for _, val in res_sum] == [1.0, None, None, 4.0]

    res_count = resample(pts, every=timedelta(minutes=1), agg="count")
    assert [val for _, val in res_count] == [1, 0, 0, 1]


def test_acceptance_item_3() -> None:
    # fill on [1.0, None, None, 4.0] gives [1.0, 2.0, 3.0, 4.0] for 'linear', [1.0, 1.0, 1.0, 4.0] for 'ffill', [1.0, 1.0, None, 4.0] for 'ffill' with limit=1, [1.0, 4.0, 4.0, 4.0] for 'bfill' and [1.0, 0.0, 0.0, 4.0] for 'zero'
    pts = [(t("00:00:00"), 1.0), (t("00:03:00"), 4.0)]
    series = resample(pts, every=timedelta(minutes=1), agg="sum")
    # series values: [1.0, None, None, 4.0]

    res_linear = fill(series, "linear")
    assert [v for _, v in res_linear] == [1.0, 2.0, 3.0, 4.0]

    res_ffill = fill(series, "ffill")
    assert [v for _, v in res_ffill] == [1.0, 1.0, 1.0, 4.0]

    res_ffill_lim1 = fill(series, "ffill", limit=1)
    assert [v for _, v in res_ffill_lim1] == [1.0, 1.0, None, 4.0]

    res_bfill = fill(series, "bfill")
    assert [v for _, v in res_bfill] == [1.0, 4.0, 4.0, 4.0]

    res_zero = fill(series, "zero")
    assert [v for _, v in res_zero] == [1.0, 0.0, 0.0, 4.0]


def test_acceptance_item_4() -> None:
    # label='right' labels the first bucket of acceptance 1 as 00:01, and origin datetime(2026, 11, 6, 0, 0, 30, tzinfo=timezone.utc) puts the 00:00:10 point in the bucket labelled datetime(2026, 11, 5, 23, 59, 30, tzinfo=timezone.utc)
    pts = [(t("00:00:10"), 1.0), (t("00:00:50"), 3.0), (t("00:01:30"), 5.0)]
    res_right = resample(pts, every=timedelta(minutes=1), agg="mean", label="right")
    assert res_right[0][0] == datetime(2026, 11, 6, 0, 1, tzinfo=timezone.utc)

    custom_origin = datetime(2026, 11, 6, 0, 0, 30, tzinfo=timezone.utc)
    res_origin = resample(
        [(t("00:00:10"), 1.0)],
        every=timedelta(minutes=1),
        agg="mean",
        origin=custom_origin,
        label="left",
    )
    assert res_origin[0][0] == datetime(2026, 11, 5, 23, 59, 30, tzinfo=timezone.utc)


def test_acceptance_item_5() -> None:
    # Input with tzinfo timezone(timedelta(hours=2)) returns UTC labels; a naive datetime raises ResampleError with code 'naive_datetime'; float('nan') raises 'invalid_value'; None values are ignored by every aggregation and not counted by 'count'
    tz_plus_2 = timezone(timedelta(hours=2))
    dt_aware = datetime(2026, 11, 6, 2, 0, 10, tzinfo=tz_plus_2)  # corresponds to 00:00:10 UTC
    res = resample([(dt_aware, 10.0)], every=timedelta(minutes=1), agg="mean")
    assert res[0][0].tzinfo == timezone.utc
    assert res[0][0] == datetime(2026, 11, 6, 0, 0, tzinfo=timezone.utc)

    naive_dt = datetime(2026, 11, 6, 0, 0, 10)
    with pytest.raises(ResampleError) as exc_info:
        resample([(naive_dt, 1.0)], every=timedelta(minutes=1), agg="mean")
    assert exc_info.value.code == "naive_datetime"

    with pytest.raises(ResampleError) as exc_val:
        resample([(t("00:00:10"), float("nan"))], every=timedelta(minutes=1), agg="mean")
    assert exc_val.value.code == "invalid_value"

    # None values ignored by every aggregation and not counted by count
    pts_with_none = [(t("00:00:10"), None), (t("00:00:20"), 5.0), (t("00:00:30"), None)]
    for agg_name in ["mean", "sum", "min", "max", "first", "last"]:
        r = resample(pts_with_none, every=timedelta(minutes=1), agg=agg_name)  # type: ignore
        assert r[0][1] == 5.0
    r_cnt = resample(pts_with_none, every=timedelta(minutes=1), agg="count")
    assert r_cnt[0][1] == 1


def test_acceptance_item_6() -> None:
    # start=00:00 and end=00:05 return exactly 5 buckets 00:00 to 00:04 even with no points; end <= start raises 'invalid_range'; every=timedelta(0) raises 'invalid_interval'; a range needing 1_000_001 buckets raises 'too_many_buckets' before allocating
    s = t("00:00:00")
    e = t("00:05:00")
    res_empty = resample([], every=timedelta(minutes=1), agg="mean", start=s, end=e)
    assert len(res_empty) == 5
    assert res_empty[0][0] == datetime(2026, 11, 6, 0, 0, tzinfo=timezone.utc)
    assert res_empty[4][0] == datetime(2026, 11, 6, 0, 4, tzinfo=timezone.utc)
    assert all(val is None for _, val in res_empty)

    with pytest.raises(ResampleError) as exc_range:
        resample([], every=timedelta(minutes=1), agg="mean", start=e, end=s)
    assert exc_range.value.code == "invalid_range"

    with pytest.raises(ResampleError) as exc_int:
        resample([], every=timedelta(0), agg="mean")
    assert exc_int.value.code == "invalid_interval"

    with pytest.raises(ResampleError) as exc_buckets:
        resample(
            [],
            every=timedelta(seconds=1),
            agg="mean",
            start=t("00:00:00"),
            end=t("00:00:00") + timedelta(seconds=1_000_001),
            max_buckets=1_000_000,
        )
    assert exc_buckets.value.code == "too_many_buckets"


def test_acceptance_item_7() -> None:
    # Shuffled input returns the same result as sorted input, 'first' and 'last' follow time order with ties in input order, and ten values 0.1 in one bucket give 'sum' 1.0 and 'mean' 0.1 exactly (math.fsum)
    shuffled = [(t("00:00:40"), 3.0), (t("00:00:10"), 1.0), (t("00:00:20"), 2.0)]
    sorted_pts = [(t("00:00:10"), 1.0), (t("00:00:20"), 2.0), (t("00:00:40"), 3.0)]
    assert resample(shuffled, every=timedelta(minutes=1), agg="first") == resample(
        sorted_pts, every=timedelta(minutes=1), agg="first"
    )
    assert resample(shuffled, every=timedelta(minutes=1), agg="last") == resample(
        sorted_pts, every=timedelta(minutes=1), agg="last"
    )

    # Ties in time follow input order
    ties = [(t("00:00:10"), 10.0), (t("00:00:10"), 20.0)]
    assert resample(ties, every=timedelta(minutes=1), agg="first")[0][1] == 10.0
    assert resample(ties, every=timedelta(minutes=1), agg="last")[0][1] == 20.0

    # 10 values of 0.1 gives 1.0 exactly for sum and 0.1 exactly for mean
    ten_pts = [(t("00:00:05"), 0.1) for _ in range(10)]
    res_sum = resample(ten_pts, every=timedelta(minutes=1), agg="sum")
    assert res_sum[0][1] == 1.0
    res_mean = resample(ten_pts, every=timedelta(minutes=1), agg="mean")
    assert res_mean[0][1] == 0.1


def test_acceptance_item_8() -> None:
    # Leading None stays None under 'linear' and 'ffill', trailing None stays None under 'linear' and 'bfill', fill([], 'linear') == [] and fill with limit=0 raises 'invalid_limit'
    series = [
        (t("00:00:00"), None),
        (t("00:01:00"), 10.0),
        (t("00:02:00"), None),
        (t("00:03:00"), 20.0),
        (t("00:04:00"), None),
    ]
    res_lin = fill(series, "linear")
    assert [v for _, v in res_lin] == [None, 10.0, 15.0, 20.0, None]

    res_ff = fill(series, "ffill")
    assert [v for _, v in res_ff] == [None, 10.0, 10.0, 20.0, 20.0]

    res_bf = fill(series, "bfill")
    assert [v for _, v in res_bf] == [10.0, 10.0, 20.0, 20.0, None]

    assert fill([], "linear") == []

    with pytest.raises(ResampleError) as exc_lim:
        fill(series, "linear", limit=0)
    assert exc_lim.value.code == "invalid_limit"


def test_bfill_with_limit() -> None:
    series = [
        (t("00:00:00"), 1.0),
        (t("00:01:00"), None),
        (t("00:02:00"), None),
        (t("00:03:00"), 4.0),
    ]
    res_bf = fill(series, "bfill", limit=1)
    assert [v for _, v in res_bf] == [1.0, None, 4.0, 4.0]


def test_linear_fill_exceeding_limit() -> None:
    series = [
        (t("00:00:00"), 1.0),
        (t("00:01:00"), None),
        (t("00:02:00"), None),
        (t("00:03:00"), 4.0),
    ]
    # Gap length is 2; limit=1 means the entire gap stays None
    res = fill(series, "linear", limit=1)
    assert [v for _, v in res] == [1.0, None, None, 4.0]


def test_validation_errors() -> None:
    # Invalid agg
    with pytest.raises(ResampleError) as exc_agg:
        resample([], every=timedelta(minutes=1), agg="unknown")  # type: ignore
    assert exc_agg.value.code == "invalid_agg"

    # Invalid fill method
    with pytest.raises(ResampleError) as exc_fill:
        fill([], "unknown")  # type: ignore
    assert exc_fill.value.code == "invalid_agg"

    # Invalid label
    with pytest.raises(ResampleError) as exc_lbl:
        resample([], every=timedelta(minutes=1), agg="mean", label="middle")  # type: ignore
    assert exc_lbl.value.code == "invalid_interval"

    # Bool value rejection
    with pytest.raises(ResampleError) as exc_bool:
        resample([(t("00:00:10"), True)], every=timedelta(minutes=1), agg="mean")  # type: ignore
    assert exc_bool.value.code == "invalid_value"

    # Non-numeric string value
    with pytest.raises(ResampleError) as exc_str:
        resample([(t("00:00:10"), "123")], every=timedelta(minutes=1), agg="mean")  # type: ignore
    assert exc_str.value.code == "invalid_value"

    # Infinity
    with pytest.raises(ResampleError) as exc_inf:
        resample([(t("00:00:10"), float("inf"))], every=timedelta(minutes=1), agg="mean")
    assert exc_inf.value.code == "invalid_value"

    # Negative timedelta
    with pytest.raises(ResampleError) as exc_neg:
        resample([], every=timedelta(seconds=-1), agg="mean")
    assert exc_neg.value.code == "invalid_interval"

    # Naive origin / start / end
    with pytest.raises(ResampleError) as exc_orig:
        resample([], every=timedelta(minutes=1), agg="mean", origin=datetime(1970, 1, 1))
    assert exc_orig.value.code == "naive_datetime"

    with pytest.raises(ResampleError) as exc_start:
        resample([], every=timedelta(minutes=1), agg="mean", start=datetime(2026, 1, 1))
    assert exc_start.value.code == "naive_datetime"

    with pytest.raises(ResampleError) as exc_end:
        resample(
            [],
            every=timedelta(minutes=1),
            agg="mean",
            start=t("00:00:00"),
            end=datetime(2026, 1, 1),
        )
    assert exc_end.value.code == "naive_datetime"

    # Max points exceeded
    with pytest.raises(ResampleError) as exc_pts:
        resample(
            [(t("00:00:00"), 1.0), (t("00:00:01"), 2.0)],
            every=timedelta(minutes=1),
            agg="mean",
            max_points=1,
        )
    assert exc_pts.value.code == "too_many_points"


def test_empty_and_no_points_without_start_end() -> None:
    assert resample([], every=timedelta(minutes=1), agg="mean") == []


def test_single_point_aggregations() -> None:
    pts = [(t("00:00:30"), 7.0)]
    assert resample(pts, every=timedelta(minutes=1), agg="min")[0][1] == 7.0
    assert resample(pts, every=timedelta(minutes=1), agg="max")[0][1] == 7.0
