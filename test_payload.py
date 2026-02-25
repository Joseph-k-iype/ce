import requests
import json
resp = requests.get("http://127.0.0.1:5001/api/admin/rules/export")
files = {'file': ('test.xlsx', resp.content, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
parse_resp = requests.post("http://127.0.0.1:5001/api/admin/rules/parse-excel", files=files)
rules = parse_resp.json()['rules']
for r in rules:
    if r['rule_id'] in ['RULE_2', 'RULE_5']:
        print(f"{r['rule_id']} - origins: {r['origin_countries']} group: {r['origin_group']}")
