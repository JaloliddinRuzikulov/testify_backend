#!/usr/bin/env python
"""Test government API directly"""

import requests
import json

PNFL = "51304025740014"
PASSPORT = "AC1987867"

url = f"http://imei_api.uzbmb.uz/compress?imie={PNFL}&ps={PASSPORT}"

print(f"Testing URL: {url}")
print("-" * 60)

try:
    response = requests.get(url, verify=False, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Content Type: {response.headers.get('content-type')}")
    print(f"Raw Response: {response.text[:500]}")
    print("-" * 60)
    
    # Try to parse as JSON
    try:
        data = response.json()
        print("JSON Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print("Response is not JSON")
        print("Text Response:")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")