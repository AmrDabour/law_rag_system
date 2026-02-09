#!/usr/bin/env python3
"""
Download Models Script
======================
Pre-download all required models before running the API.
This is useful for containerized environments.

Usage:
    python scripts/download_models.py
"""

import os
import sys


def download_embedding_model():
    """Download Qwen3 embedding model"""
    print("Downloading embedding model: Qwen/Qwen3-Embedding-0.6B...")
    
    from sentence_transformers import SentenceTransformer
    
    model = SentenceTransformer(
        "Qwen/Qwen3-Embedding-0.6B",
        trust_remote_code=True,
        device="cpu",
    )
    
    # Test
    test = model.encode(["اختبار"])
    print(f"   ✅ Embedding dimension: {len(test[0])}")
    return True


def download_sparse_model():
    """Download BM25 sparse encoder"""
    print("Downloading sparse encoder: Qdrant/bm25...")
    
    from fastembed import SparseTextEmbedding
    
    model = SparseTextEmbedding(
        model_name="Qdrant/bm25",
    )
    
    # Test
    test = list(model.embed(["اختبار"]))[0]
    print(f"   ✅ Sparse values count: {len(test.values)}")
    return True


def download_reranker_model():
    """Download Qwen3 reranker model"""
    print("Downloading reranker model: Qwen/Qwen3-Reranker-0.6B...")
    
    from sentence_transformers import CrossEncoder
    
    model = CrossEncoder(
        "Qwen/Qwen3-Reranker-0.6B",
        trust_remote_code=True,
        device="cpu",
    )
    
    # Test
    test = model.predict([("سؤال", "إجابة")])
    print(f"   ✅ Reranker score: {test[0]:.4f}")
    return True


def main():
    print("=" * 60)
    print("Egyptian Law RAG - Model Download")
    print("=" * 60)
    print()
    
    results = []
    
    # 1. Embedding model
    try:
        download_embedding_model()
        results.append(("Embedding", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("Embedding", False))
    
    print()
    
    # 2. Sparse encoder
    try:
        download_sparse_model()
        results.append(("Sparse", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("Sparse", False))
    
    print()
    
    # 3. Reranker
    try:
        download_reranker_model()
        results.append(("Reranker", True))
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results.append(("Reranker", False))
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_success = True
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
        if not success:
            all_success = False
    
    print("=" * 60)
    
    if all_success:
        print("✅ All models downloaded successfully!")
    else:
        print("❌ Some models failed to download.")
        sys.exit(1)


if __name__ == "__main__":
    main()
