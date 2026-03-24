#!/usr/bin/env python3
"""
test_scan.py
============
Test script to send a dataset to the compliance backend and save the scan result.

Usage:
    python test_scan.py sample_dataset.json
    python test_scan.py sample_dataset_clean.json
"""

import sys
import json
import requests

def scan_dataset(dataset_file, backend_url="http://localhost:8000"):
    """Send dataset JSON to the compliance backend and return scan result."""
    
    # Read the dataset file
    with open(dataset_file, 'r') as f:
        payload = json.load(f)
    
    # POST to /compliance/scan
    print(f"📤 Sending {dataset_file} to {backend_url}/compliance/scan ...")
    
    try:
        response = requests.post(
            f"{backend_url}/compliance/scan",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Save the result
        output_file = dataset_file.replace('.json', '_scan_result.json')
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Print summary
        print(f"✅ Scan complete!")
        print(f"📊 Overall Status: {result['overall_status'].upper()}")
        print(f"🔍 Total Findings: {len(result['findings'])}")
        print(f"📁 Result saved to: {output_file}")
        
        # Breakdown by severity
        severity_counts = {}
        for finding in result['findings']:
            sev = finding['severity']
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        print(f"\n📈 Findings by Severity:")
        for sev in ['critical', 'high', 'medium', 'low']:
            count = severity_counts.get(sev, 0)
            if count > 0:
                emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}[sev]
                print(f"   {emoji} {sev.upper()}: {count}")
        
        # Breakdown by regulation
        print(f"\n🌍 Status by Regulation:")
        for reg, status in result['summary'].items():
            emoji = '✅' if status == 'compliant' else '❌' if status == 'non_compliant' else '⏳'
            print(f"   {emoji} {reg}: {status}")
        
        return result
        
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to backend.")
        print("   Make sure the backend is running:")
        print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"   Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_scan.py <dataset.json>")
        print("\nExamples:")
        print("  python test_scan.py sample_dataset.json")
        print("  python test_scan.py sample_dataset_clean.json")
        sys.exit(1)
    
    dataset_file = sys.argv[1]
    scan_dataset(dataset_file)
