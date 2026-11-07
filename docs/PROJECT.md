# Project Information

`timeseries-resample` is a zero-dependency Python utility library for irregular time-series resampling and gap filling.

## Goals
- Pure Python standard library implementation.
- Deterministic microsecond-precision bucketing using `timedelta` arithmetic.
- Accurate floating-point summations via `math.fsum`.
- Strict validation of timestamps and input values.

## Scope
- Resampling irregular series to fixed UTC grids.
- Gap filling via ffill, bfill, linear, and zero methods.
- Error handling for invalid inputs (out-of-range, bad types, naive datetimes).

## Out of Scope
- Calendar-aware intervals (months, years).
- Rolling/expanding windows.
- Advanced interpolation (non-linear).
- Multivariate series (multiple values per timestamp).
- Timezone database lookups.

## Factory run u168 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4543 | 10444 | 0 | 0 | 0.0213 |
| fix-1 | gemini-3.8-flash | no | 17579 | 532 | 0 | 27127 | 0.0172 |
| fix-2 | gemini-3.8-flash | no | 33273 | 1720 | 0 | 94359 | 0.0385 |
| fix-3 | gemini-3.8-flash | no | 12796 | 195 | 0 | 8495 | 0.0110 |
| audit | gemini-3.1-flash-lite | no | 50648 | 475 | 0 | 95569 | 0.0158 |
| docs | gemini-3.1-flash-lite | no | 201895 | 1876 | 0 | 0 | 0.0533 |

Total: $0.1570. Prices: Anthropic list prices.
