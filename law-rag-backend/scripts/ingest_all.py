#!/usr/bin/env python3
"""
Ingest All Egyptian Laws
========================
Batch ingestion script for all Egyptian law PDFs.

Usage:
    python scripts/ingest_all.py [--country egypt] [--base-url http://localhost:8000]
"""

import os
import sys
import argparse
import httpx
import time
from pathlib import Path
from typing import List, Dict, Any

# === Egyptian Laws Metadata ===
EGYPT_LAWS = [
    {
        "file": "القانون الجنائي.pdf",
        "law_type": "criminal",
        "law_name": "قانون العقوبات",
        "law_name_en": "Penal Code",
        "law_number": "58",
        "law_year": "1937",
    },
    {
        "file": "القانون المدني.pdf",
        "law_type": "civil",
        "law_name": "القانون المدني",
        "law_name_en": "Civil Code",
        "law_number": "131",
        "law_year": "1948",
    },
    {
        "file": "القانون الاقتصادي.pdf",
        "law_type": "economic",
        "law_name": "قانون الاقتصاد",
        "law_name_en": "Economic Law",
        "law_number": "",
        "law_year": "",
    },
]

# === Country Mappings ===
COUNTRY_LAWS = {
    "egypt": {
        "folder": "Egyptian",
        "laws": EGYPT_LAWS,
    },
    # Add more countries here:
    # "jordan": {
    #     "folder": "Jordanian",
    #     "laws": JORDAN_LAWS,
    # },
}


def ingest_law(
    base_url: str,
    file_path: Path,
    country: str,
    metadata: Dict[str, Any],
    timeout: float = 300.0,
) -> Dict[str, Any]:
    """
    Ingest a single law PDF.
    
    Args:
        base_url: API base URL
        file_path: Path to PDF file
        country: Country code
        metadata: Law metadata
        timeout: Request timeout in seconds
        
    Returns:
        API response dict
    """
    url = f"{base_url}/api/v1/ingest"
    
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "application/pdf")}
        data = {
            "country": country,
            "law_type": metadata["law_type"],
            "law_name": metadata["law_name"],
            "law_name_en": metadata.get("law_name_en", ""),
            "law_number": metadata.get("law_number", ""),
            "law_year": metadata.get("law_year", ""),
        }
        
        response = httpx.post(
            url,
            files=files,
            data=data,
            timeout=timeout,
        )
        
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Ingest all laws for a country")
    parser.add_argument(
        "--country",
        type=str,
        default="egypt",
        choices=list(COUNTRY_LAWS.keys()),
        help="Country to ingest laws for",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="API base URL",
    )
    parser.add_argument(
        "--laws-dir",
        type=str,
        default=None,
        help="Base directory containing law materials",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Request timeout in seconds",
    )
    
    args = parser.parse_args()
    
    # Determine laws directory
    if args.laws_dir:
        laws_base = Path(args.laws_dir)
    else:
        # Default: look for law_material in parent or current directory
        script_dir = Path(__file__).parent.parent
        laws_base = script_dir / "law_material"
        if not laws_base.exists():
            laws_base = script_dir.parent / "law_material"
    
    if not laws_base.exists():
        print(f"❌ Laws directory not found: {laws_base}")
        sys.exit(1)
    
    # Get country config
    country_config = COUNTRY_LAWS.get(args.country)
    if not country_config:
        print(f"❌ Unknown country: {args.country}")
        sys.exit(1)
    
    country_dir = laws_base / country_config["folder"]
    if not country_dir.exists():
        print(f"❌ Country directory not found: {country_dir}")
        sys.exit(1)
    
    laws = country_config["laws"]
    
    print("=" * 60)
    print(f"Egyptian Law RAG - Batch Ingestion")
    print("=" * 60)
    print(f"Country: {args.country}")
    print(f"Laws directory: {country_dir}")
    print(f"API URL: {args.base_url}")
    print(f"Laws to ingest: {len(laws)}")
    print("=" * 60)
    
    # Check API health
    try:
        response = httpx.get(f"{args.base_url}/health", timeout=10.0)
        health = response.json()
        if health.get("status") != "healthy":
            print(f"⚠️ API not fully healthy: {health}")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        sys.exit(1)
    
    print("✅ API is healthy\n")
    
    # Ingest each law
    results = []
    total_articles = 0
    total_chunks = 0
    
    for i, law in enumerate(laws, 1):
        file_path = country_dir / law["file"]
        
        print(f"[{i}/{len(laws)}] Processing: {law['law_name']}")
        print(f"    File: {file_path.name}")
        
        if not file_path.exists():
            print(f"    ⚠️ SKIPPED - File not found: {file_path}")
            results.append({"law": law["law_name"], "status": "skipped", "error": "File not found"})
            continue
        
        start_time = time.time()
        
        try:
            result = ingest_law(
                base_url=args.base_url,
                file_path=file_path,
                country=args.country,
                metadata=law,
                timeout=args.timeout,
            )
            
            elapsed = time.time() - start_time
            
            if result.get("success"):
                articles = result.get("articles_found", 0)
                chunks = result.get("chunks_created", 0)
                total_articles += articles
                total_chunks += chunks
                
                print(f"    ✅ SUCCESS - {articles} articles, {chunks} chunks ({elapsed:.1f}s)")
                results.append({"law": law["law_name"], "status": "success", "articles": articles, "chunks": chunks})
            else:
                print(f"    ❌ FAILED - {result.get('detail', 'Unknown error')}")
                results.append({"law": law["law_name"], "status": "failed", "error": result.get("detail")})
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"    ❌ ERROR - {str(e)} ({elapsed:.1f}s)")
            results.append({"law": law["law_name"], "status": "error", "error": str(e)})
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] in ("failed", "error"))
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    
    print(f"Total Laws: {len(laws)}")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Failed:  {failed_count}")
    print(f"  ⚠️ Skipped: {skipped_count}")
    print(f"\nTotal Articles: {total_articles}")
    print(f"Total Chunks:   {total_chunks}")
    print("=" * 60)
    
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
