# Security

`timeseries_resample` processes time series datasets, which may contain adversarial input.

## Threat Model

### Defended
- **Denial of Service (DoS)**: Memory exhaustion is mitigated by explicit constraints on input size (`max_points` default 1,000,000) and output size (`max_buckets` default 1,000,000). These limits are enforced before heavy computation occurs.
- **Invalid Input**: The library rejects `bool` types, `NaN` or `infinity` floating-point values, and naive datetimes, preventing corrupted state or crashes.
- **Error Information Leakage**: Exception messages are explicitly truncated to 200 characters and do not echo raw, potentially secret-laden user inputs.

### Not Defended
- **Resource Exhaustion (Computation)**: While memory usage is limited by bucket counts, highly dense, valid input datasets may still require non-trivial CPU time for sorting and aggregation.
