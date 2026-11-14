"""Bake only the pinned, public MiniLM snapshot into the image; no credentials or profiles."""
from huggingface_hub import snapshot_download

snapshot_download('sentence-transformers/all-MiniLM-L6-v2',
    revision='1110a243fdf4706b3f48f1d95db1a4f5529b4d41',
    allow_patterns=['*.json', '*.safetensors', 'vocab.txt', 'tokenizer.*', '*.txt', '1_Pooling/*'])
