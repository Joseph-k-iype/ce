import requests
import pandas as pd
import io

df = pd.DataFrame([{"Requires PII": "TRUE", "rule id": "RULE_X"}])
buf = io.BytesIO()
df.to_excel(buf, index=False)
buf.seek(0)
files = {'file': ('test.xlsx', buf, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
resp = requests.post("http://127.0.0.1:5001/api/admin/rules/parse-excel", files=files)
print(resp.json())
