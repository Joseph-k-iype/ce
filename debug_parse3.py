import pandas as pd
df = pd.DataFrame([{"Requires PII": "TRUE", "rule id": "RULE_X"}])
df.columns = [str(c).strip().lower() for c in df.columns]
for idx, row in df.iterrows():
    def val(col_names):
        for c in col_names:
            if c in df.columns:
                v = row[c]
                if pd.isna(v): return ""
                return str(v).strip()
        return ""
    
    requires_pii_val = val(['requires pii', 'requires_pii']).lower()
    print("requires_pii_val =", repr(requires_pii_val))
    requires_pii = requires_pii_val in ['true', 'yes', '1', 'y']
    print("requires_pii =", requires_pii)
