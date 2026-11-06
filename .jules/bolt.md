# Bolt's Performance Journal

## 2026-10-27 - Vectorizing Recursive Indicators in Quantitative Pipelines
**Learning:** In pandas technical analysis code (such as Supertrend or trailing stop bands), recursive state calculations that iterate through bars using `series.iloc[i]` carry massive Python overhead (~625ms for 5,000 candles). Converting the inputs to 1D NumPy arrays via `.to_numpy()`, iterating over contiguous memory, and mutating preallocated NumPy buffers (`np.full(n, np.nan)`) drops execution time to ~19ms (>30x speedup) with 100% numerical equivalence.
**Action:** When sequential/recursive loops over price bars are unavoidable (cannot be expressed as purely vectorized window rolls), immediately convert inputs to NumPy arrays (`.to_numpy()`) instead of indexing `pd.Series` via `.iloc`.
