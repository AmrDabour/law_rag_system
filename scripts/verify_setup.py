#!/usr/bin/env python3
"""
Verify Setup Script
===================
Verify that all components are working correctly.

Usage:
    python scripts/verify_setup.py [--base-url http://localhost:8000]
"""

import sys
import argparse
import httpx
from typing import Dict, Any, Tuple


def check_health(base_url: str) -> Tuple[bool, Dict[str, Any]]:
    """Check API health"""
    try:
        response = httpx.get(f"{base_url}/health", timeout=10.0)
        data = response.json()
        return data.get("status") == "healthy", data
    except Exception as e:
        return False, {"error": str(e)}


def check_ready(base_url: str) -> Tuple[bool, Dict[str, Any]]:
    """Check API readiness"""
    try:
        response = httpx.get(f"{base_url}/ready", timeout=30.0)
        data = response.json()
        return data.get("ready", False), data
    except Exception as e:
        return False, {"error": str(e)}


def check_laws(base_url: str) -> Tuple[bool, Dict[str, Any]]:
    """Check laws endpoint"""
    try:
        response = httpx.get(f"{base_url}/api/v1/laws", timeout=10.0)
        data = response.json()
        return data.get("success", False), data
    except Exception as e:
        return False, {"error": str(e)}


def test_query(base_url: str, country: str = "egypt") -> Tuple[bool, Dict[str, Any]]:
    """Test query endpoint"""
    try:
        response = httpx.post(
            f"{base_url}/api/v1/query",
            json={
                "question": "ما هي عقوبة السرقة؟",
                "country": country,
                "top_k": 3,
            },
            timeout=60.0,
        )
        data = response.json()
        return data.get("success", False), data
    except Exception as e:
        return False, {"error": str(e)}


def test_session(base_url: str) -> Tuple[bool, Dict[str, Any]]:
    """Test session creation"""
    try:
        response = httpx.post(
            f"{base_url}/api/v1/sessions",
            json={"country": "egypt"},
            timeout=10.0,
        )
        data = response.json()
        return "session_id" in data, data
    except Exception as e:
        return False, {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Verify system setup")
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="API base URL",
    )
    parser.add_argument(
        "--test-query",
        action="store_true",
        help="Also test query endpoint (requires ingested laws)",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Egyptian Law RAG - Setup Verification")
    print("=" * 60)
    print(f"API URL: {args.base_url}")
    print("=" * 60 + "\n")
    
    all_passed = True
    
    # 1. Health Check
    print("1. Health Check...")
    passed, data = check_health(args.base_url)
    if passed:
        print(f"   ✅ PASSED - Status: {data.get('status')}")
        print(f"      Qdrant: {data.get('qdrant')}")
        print(f"      Redis:  {data.get('redis')}")
    else:
        print(f"   ❌ FAILED - {data}")
        all_passed = False
    
    # 2. Readiness Check
    print("\n2. Readiness Check...")
    passed, data = check_ready(args.base_url)
    if passed:
        print(f"   ✅ PASSED - All models loaded")
        print(f"      Services: {data.get('services')}")
        print(f"      Models:   {data.get('models_loaded')}")
    else:
        print(f"   ⚠️ PARTIAL - Some models may not be ready")
        print(f"      Services: {data.get('services')}")
        print(f"      Models:   {data.get('models_loaded')}")
    
    # 3. Laws Endpoint
    print("\n3. Laws Endpoint...")
    passed, data = check_laws(args.base_url)
    if passed:
        print(f"   ✅ PASSED - Laws endpoint accessible")
        countries = data.get("countries", {})
        for country, info in countries.items():
            status = info.get("status", "unknown")
            points = info.get("points_count", 0)
            print(f"      {country}: {status} ({points} points)")
    else:
        print(f"   ❌ FAILED - {data}")
        all_passed = False
    
    # 4. Session Creation
    print("\n4. Session Creation...")
    passed, data = check_session(args.base_url)
    if passed:
        print(f"   ✅ PASSED - Session ID: {data.get('session_id')[:8]}...")
    else:
        print(f"   ❌ FAILED - {data}")
        all_passed = False
    
    # 5. Query Test (optional)
    if args.test_query:
        print("\n5. Query Test...")
        passed, data = test_query(args.base_url)
        if passed:
            print(f"   ✅ PASSED - Query returned answer")
            print(f"      Sources: {len(data.get('sources', []))}")
            print(f"      Time:    {data.get('metadata', {}).get('query_time_ms', 0):.0f}ms")
        else:
            if "No laws found" in str(data.get("detail", "")):
                print(f"   ⚠️ SKIPPED - No laws ingested yet")
            else:
                print(f"   ❌ FAILED - {data}")
                all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All checks passed!")
        print("\nNext steps:")
        print("  1. Ingest laws: python scripts/ingest_all.py")
        print("  2. Test queries: curl -X POST http://localhost:8000/api/v1/query \\")
        print('       -H "Content-Type: application/json" \\')
        print('       -d \'{"question": "ما هي عقوبة السرقة؟", "country": "egypt"}\'')
    else:
        print("❌ Some checks failed. Please review the errors above.")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
