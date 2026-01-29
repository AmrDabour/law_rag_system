#!/usr/bin/env python3
"""
Ingest All Laws - Dynamic Scanner
=================================
Batch ingestion script that automatically discovers and ingests all PDF files
in the laws directory. No need to manually add each law file.

Usage:
    python scripts/ingest_all.py [--country egypt] [--base-url http://localhost:8000]
    python scripts/ingest_all.py --country egypt --file "القانون المدني.pdf"  # Single file
"""

import os
import sys
import argparse
import httpx
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# === Country Folder Mappings ===
COUNTRY_FOLDERS = {
    "egypt": "Egyptian",
    "jordan": "Jordanian",
    "uae": "UAE",
    "saudi": "Saudi",
    "kuwait": "Kuwaiti",
}

# === Law Type Detection (from filename) ===
LAW_TYPE_KEYWORDS = {
    "جنائي": "criminal",
    "عقوبات": "criminal",
    "جنايات": "criminal",
    "مدني": "civil",
    "تجاري": "commercial",
    "اقتصادي": "economic",
    "تحكيم": "arbitration",
    "عمل": "labor",
    "أحوال شخصية": "personal_status",
    "إداري": "administrative",
}


def detect_law_type(filename: str) -> str:
    """Detect law type from filename using keywords."""
    for keyword, law_type in LAW_TYPE_KEYWORDS.items():
        if keyword in filename:
            return law_type
    return "general"


def generate_law_metadata(pdf_path: Path) -> Dict[str, Any]:
    """
    Generate metadata for a PDF file based on its filename.

    The filename is used as the law name, and law type is auto-detected.
    """
    filename = pdf_path.stem  # filename without extension

    return {
        "file": pdf_path.name,
        "law_type": detect_law_type(filename),
        "law_name": filename,
        "law_name_en": "",  # Can be filled manually if needed
        "law_number": "",
        "law_year": "",
    }


def discover_laws(country_dir: Path) -> List[Dict[str, Any]]:
    """
    Discover all PDF files in a directory and generate metadata for each.

    Args:
        country_dir: Path to the country's law directory

    Returns:
        List of law metadata dicts
    """
    laws = []

    # Find all PDF files
    pdf_files = sorted(country_dir.glob("*.pdf"))

    for pdf_path in pdf_files:
        metadata = generate_law_metadata(pdf_path)
        laws.append(metadata)

    return laws


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
        choices=list(COUNTRY_FOLDERS.keys()),
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
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Ingest a single file instead of all files (filename only)",
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

    # Get country folder
    country_folder = COUNTRY_FOLDERS.get(args.country)
    if not country_folder:
        print(f"❌ Unknown country: {args.country}")
        print(f"   Available: {', '.join(COUNTRY_FOLDERS.keys())}")
        sys.exit(1)

    country_dir = laws_base / country_folder
    if not country_dir.exists():
        print(f"❌ Country directory not found: {country_dir}")
        print(f"   Please create it and add PDF files")
        sys.exit(1)

    # Discover laws dynamically from the directory
    laws = discover_laws(country_dir)

    # Filter to single file if specified
    if args.file:
        laws = [l for l in laws if l["file"] == args.file]
        if not laws:
            print(f"❌ File not found: {args.file}")
            print(f"   Available files in {country_dir}:")
            for pdf in country_dir.glob("*.pdf"):
                print(f"     - {pdf.name}")
            sys.exit(1)
    
    print("=" * 60)
    print(f"Law RAG - Dynamic Batch Ingestion")
    print("=" * 60)
    print(f"Country: {args.country}")
    print(f"Laws directory: {country_dir}")
    print(f"API URL: {args.base_url}")
    print(f"PDF files found: {len(laws)}")
    if args.file:
        print(f"Single file mode: {args.file}")
    print("=" * 60)

    if len(laws) == 0:
        print("⚠️ No PDF files found in directory")
        sys.exit(0)
    
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
