import pandas as pd
import numpy as np
import timeit

def generate_df(rows):
    data = []
    for _ in range(rows):
        data.append([
            '2023-01-01T00:00:00',
            str(np.random.rand() * 100),
            str(np.random.rand() * 100),
            str(np.random.rand() * 100),
            str(np.random.rand() * 100),
            str(int(np.random.rand() * 1000))
        ])
    return pd.DataFrame(data, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])

df_base = generate_df(1000)

def test_iterative(df):
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def test_vectorized_apply(df):
    cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
    return df

if __name__ == "__main__":
    t1 = timeit.timeit(lambda: test_iterative(df_base.copy()), number=100)
    print(f"Iterative: {t1:.4f} seconds")

    t2 = timeit.timeit(lambda: test_vectorized_apply(df_base.copy()), number=100)
    print(f"Vectorized (apply): {t2:.4f} seconds")
