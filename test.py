from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Reranker-0.6B", trust_remote_code=True)
print(f"pad_token: {tokenizer.pad_token}")
print(f"pad_token_id: {tokenizer.pad_token_id}")
print(f"eos_token: {tokenizer.eos_token}")
print(f"eos_token_id: {tokenizer.eos_token_id}")

# Test tokenization
pairs = [["query1", "doc1"], ["query2", "doc2"]]
try:
    inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt", max_length=512)
    print("Tokenization SUCCESS")
except Exception as e:
    print(f"Tokenization FAILED: {e}")
