import pandas as pd
df = pd.DataFrame([{"requires pii": "TRUE"}])
for idx, row in df.iterrows():
    v = row['requires pii']
    print(v)
    print(pd.isna(v))
    print(str(v).strip().lower())
