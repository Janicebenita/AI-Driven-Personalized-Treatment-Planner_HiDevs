"""Bake only the pinned, public MiniLM snapshot into the image; no credentials or profiles."""
from huggingface_hub import snapshot_download

from rag.config import EmbeddingConfig

config = EmbeddingConfig.from_env()
snapshot_download(config.model_id,
    revision=config.revision,
    allow_patterns=['*.json', '*.safetensors', 'vocab.txt', 'tokenizer.*', '*.txt', '1_Pooling/*'])
