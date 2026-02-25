import requests
import pandas as pd
import io
import json

BASE_URL = "http://127.0.0.1:5001/api"

print("1. Downloading export...")
resp = requests.get(f"{BASE_URL}/admin/rules/export")
if resp.status_code != 200:
    print(f"Failed to export: {resp.status_code} {resp.text}")
    exit(1)

df = pd.read_excel(io.BytesIO(resp.content))
print(f"Exported {len(df)} rules.")
df.columns = [str(c).strip() for c in df.columns]

print("2. Modifying RULE_2 logic tree...")
rule_idx = df[df['Rule ID'] == 'RULE_2'].index
if len(rule_idx) == 0:
    print("RULE_2 not found!")
    exit(1)

idx = rule_idx[0]
new_logic = {
    "type": "AND",
    "children": [
        {"type": "CONDITION", "dimension": "Regulator", "value": "TEST_REGULATOR_XYZ"}
    ]
}
for r_idx in rule_idx:
    df.loc[r_idx, 'Logic Tree JSON'] = json.dumps(new_logic)
    df.loc[r_idx, 'Requires PII'] = 'TRUE'

buf = io.BytesIO()
df.to_excel(buf, index=False)
buf.seek(0)

print("3. Uploading modified Excel to parse-excel...")
files = {'file': ('test_mod.xlsx', buf, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
parse_resp = requests.post(f"{BASE_URL}/admin/rules/parse-excel", files=files)
if parse_resp.status_code != 200:
    print(f"Failed to parse: {parse_resp.status_code} {parse_resp.text}")
    exit(1)

parsed_data = parse_resp.json()
rules_to_insert = parsed_data['rules']
print(f"Parsed {len(rules_to_insert)} rules.")

print("4. Pushing rules to graph...")
push_resp = requests.post(f"{BASE_URL}/admin/rules/bulk-insert", json=rules_to_insert)
if push_resp.status_code != 200:
    print(f"Failed to push: {push_resp.status_code} {push_resp.text}")
    exit(1)

print("Push successful:", push_resp.json())

print("5. Evaluating rule with TEST_REGULATOR_XYZ and PII...")
eval_payload = {
    "origin_country": "Germany", # RULE_2 operates on EU_EEA origin
    "receiving_country": "United Kingdom", # ADEQUACY_COUNTRIES member
    "pii": True,
    "regulator": ["TEST_REGULATOR_XYZ"],
    "personal_data_names": ["Email"]
}
eval_resp = requests.post(f"{BASE_URL}/evaluate-rules", json=eval_payload)
if eval_resp.status_code != 200:
    print(f"Failed evaluation: {eval_resp.status_code} {eval_resp.text}")
    exit(1)

eval_data = eval_resp.json()
triggered = [r['rule_id'] for r in eval_data.get('triggered_rules', [])]
print(f"Triggered rules: {triggered}")

if 'RULE_2' in triggered:
    print("SUCCESS! RULE_2 fired with the modified logic.")
else:
    print("FAILURE! RULE_2 did not fire. Logic was not correctly persisted or evaluated.")
    
eval_payload["pii"] = False
eval_resp = requests.post(f"{BASE_URL}/evaluate-rules", json=eval_payload)
triggered_no_pii = [r['rule_id'] for r in eval_resp.json().get('triggered_rules', [])]
if 'RULE_2' not in triggered_no_pii:
    print("SUCCESS! RULE_2 did NOT fire when PII=False.")
else:
    print("FAILURE! RULE_2 fired even though PII=False and requires_pii=TRUE.")

print("All E2E checks completed.")
