# M2 Benchmark Report — Smart Import vs Tessellated Baseline

Date: 2026-02-21  
Branch: `phase3/perf-benchmark-harness`

## Scope

This report closes M2 Issue #10 by publishing baseline benchmark results and defining initial regression thresholds.

Benchmark harness:
- `scripts/benchmark_smart_import.py`
- `scripts/summarize_smart_import_benchmark.py`

## Test Scenes

1. `L9HF60-SwagelokCompany-3D-07-01-2025.stp` (small)
2. `NUC13ANB_NUC13LCB.STP` (large)

## Results (import-only)

| Scene | Baseline Import (s) | Smart Import (s) | Delta | Imported Solids | Smart Primitive Selected | Smart Primitive Ratio |
|---|---:|---:|---:|---:|---:|---:|
| L9HF60 | 0.089 | 0.126 | +41.0% | 1 | 0 | 0.00% |
| NUC13 | 14.606 | 17.939 | +22.82% | 289 | 16 | 5.54% |

## Interpretation

- Current smart-import implementation introduces import-time overhead versus tessellated baseline on both scenes.
- For the larger scene, smart import already maps a measurable subset to primitives (16/289, 5.54%), which is useful for tracking model coverage progress in M2/M3.
- No import-time speedup is claimed yet; this baseline is intended to support future hardening/optimization work.

## Initial Regression Thresholds

Defined in `benchmarks/thresholds/m2_thresholds.json`:

- **L9HF60 (small)**
  - max import overhead: `+60%`
  - min selected primitive ratio: `0.00`

- **NUC13 (large)**
  - max import overhead: `+35%`
  - min selected primitive ratio: `0.04`

These thresholds are intentionally conservative for initial CI gating and should be tightened as smart-import performance improves.

## Validation Command

```bash
python scripts/check_benchmark_thresholds.py \
  --thresholds benchmarks/thresholds/m2_thresholds.json \
  --result benchmarks/results/<result_file>.json
```

Exit code is non-zero when any threshold fails.
