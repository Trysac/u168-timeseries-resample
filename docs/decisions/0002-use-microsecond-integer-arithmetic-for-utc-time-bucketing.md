# Use microsecond integer arithmetic for UTC time bucketing

Status: accepted (generated, pending human review)

## Context

Floating-point or naive date math can lead to subtle boundary misalignments, especially around daylight saving time transitions or microsecond offsets.

## Decision

All datetimes are strictly enforced to be timezone-aware and normalized to UTC. Buckets are computed using exact integer microsecond floor division relative to an aware origin point. Aggregations use math.fsum for numerical precision.

## Consequences

Boundary conditions are completely deterministic and immune to local DST shifts. Calendar-based intervals (months/years) are out of scope.
