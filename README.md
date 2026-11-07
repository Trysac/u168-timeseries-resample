# timeseries-resample

[![PyPI version](https://img.shields.io/pypi/v/trysac-timeseries-resample)](https://pypi.org/project/trysac-timeseries-resample/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-timeseries-resample)](LICENSE)
[![CI](https://github.com/Trysac/u168-timeseries-resample/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u168-timeseries-resample/actions/workflows/ci.yml)

Resample irregular time series into fixed UTC buckets with seven aggregations and fill gaps by forward, backward, linear time-weighted or zero fill with limits

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-timeseries-resample
# or
uv add trysac-timeseries-resample
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import timeseries_resample

# normalize() trims surrounding whitespace and lower-cases the text.
print(timeseries_resample.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    timeseries_resample.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
