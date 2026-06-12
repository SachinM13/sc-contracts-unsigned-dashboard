#!/usr/bin/env python3
"""Student Cribs Contracts Unsigned Dashboard — Daily Generator"""
import os, json, xml.etree.ElementTree as ET, urllib.request, sys
from datetime import date
from collections import defaultdict

AUTH = os.environ.get('SC_API_AUTH', '')
if not AUTH:
    print("ERROR: SC_API_AUTH not set", file=sys.stderr)
    sys.exit(1)

BASE = "https://api.student-cribs.com/api/xmls/remarket_flag/"

def fetch():
    url = f"{BASE}?auth={AUTH}"
    print(f"  Fetching contracts unsigned...", file=sys.stderr)
    req = urllib.request.Request(url, headers={'User-Agent': 'SC-Dashboard/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            content = r.read()
        root = ET.fromstring(content)
        return root.findall('.//contract')
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return []

def agg(contracts):
    cities = defaultdict(int)
    regions = defaultdict(int)
    days_buckets = {'0-7': 0, '8-14': 0, '15-30': 0, '31-60': 0, '61-90': 0, '90+': 0}
    urgent = []
    total = len(contracts)
    total_days = 0
    for c in contracts:
        city = (c.findtext('city_name') or '').strip()
        if city: cities[city] += 1
        region = (c.findtext('region_name') or '').strip()
        if region: regions[region] += 1
        days = int((c.findtext('contract_out_days') or '0').strip() or 0)
        total_days += days
        if days <= 7: days_buckets['0-7'] += 1
        elif days <= 14: days_buckets['8-14'] += 1
        elif days <= 30: days_buckets['15-30'] += 1
        elif days <= 60: days_buckets['31-60'] += 1
        elif days <= 90: days_buckets['61-90'] += 1
        else: days_buckets['90+'] += 1
        if days >= 14:
            urgent.append({
                'property': (c.findtext('property_name') or '').strip(),
                'city': city,
                'tenant': (c.findtext('lead_tenant_full_name') or '').strip(),
                'days': days,
                'sent': (c.findtext('contract_sent_at') or '').strip()[:10],
            })
    urgent.sort(key=lambda x: -x['days'])
    return {
        'total': total,
        'avg_days': round(total_days / total, 1) if total > 0 else 0,
        'cities': sorted(cities.items(), key=lambda x: -x[1])[:15],
        'regions': sorted(regions.items(), key=lambda x: -x[1]),
        'days_buckets': days_buckets,
        'urgent': urgent[:30],
    }

today = date.today()
print("Fetching data...", file=sys.stderr)
contracts = fetch()
data = agg(contracts)
meta = {'generated': today.strftime('%d %b %Y'), 'total': data['total']}
data_js = f"""const DATA = {json.dumps(data)};
const META = {json.dumps(meta)};"""
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, 'template.html'), 'r', encoding='utf-8') as f:
    html = f.read()
html = html.replace('// <!--INJECT_DATA-->', data_js)
with open(os.path.join(script_dir, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(html)
print("Done!", file=sys.stderr)
