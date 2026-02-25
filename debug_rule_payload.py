import requests
resp = requests.get("http://127.0.0.1:5001/api/admin/rules/export")
import pandas as pd
import io
df = pd.read_excel(io.BytesIO(resp.content))
df.columns = [str(c).strip().lower() for c in df.columns]

for idx, row in df.iterrows():
    def val(col_names):
        for c in col_names:
            if c in df.columns:
                v = row[c]
                if pd.isna(v): return ""
                return str(v).strip()
        return ""
    if val(['rule id']) == 'RULE_2':
        origins = val(['origin countries', 'origin_countries', 'origin'])
        print(origins)
        origins = [x.strip() for x in origins.split(',') if x.strip()]
        print("Origins Array:", origins)
