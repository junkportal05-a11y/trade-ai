## 2025-02-23 - NumPy Array Conversion for Sequential Indicator Loops
**Learning:** Iterating through pandas Series using `.iloc[i]` in sequential loops (like Supertrend calculation) incurs significant pandas overhead (~70ms per 500-bar DataFrame). Extracting underlying NumPy arrays using `.values` before the loop reduces iteration time by ~40-50x (~1.5ms).
**Action:** Always extract `.values` or convert to NumPy arrays before writing explicit Python `for` loops over pandas Series in data processing pipelines.
