#!/usr/bin/env python3
"""Add oncall fields to all employees"""
import json

# Read the org data
with open('data/org_data.json', 'r') as f:
    data = json.load(f)

# Add oncall fields to employees that don't have them
updated_count = 0
for emp in data['employees']:
    if 'is_on_call' not in emp:
        emp['is_on_call'] = False
        emp['on_call_role'] = None
        emp['emergency_auth_level'] = emp.get('security_clearance', 'standard')
        updated_count += 1

# Write back
with open('data/org_data.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f'✅ Updated {updated_count} employees with oncall fields')
print(f'📊 Total employees: {len(data["employees"])}')

# Show oncall employees
oncall = [e for e in data['employees'] if e.get('is_on_call')]
print(f'🚨 On-call employees: {len(oncall)}')
for e in oncall:
    print(f'  - {e["name"]}: {e["on_call_role"]} (auth: {e["emergency_auth_level"]})')
