"""Behavior tests for the public API of timeseries_resample."""

from __future__ import annotations

import pytest

import timeseries_resample


def test_normalize_trims_and_lowercases() -> None:
    assert timeseries_resample.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        timeseries_resample.normalize(value)


def test_version_is_semver() -> None:
    parts = timeseries_resample.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
