"""Validated, pinned embedding configuration; no credentials in this object."""
import os
import re
from dataclasses import dataclass

DEFAULT_MODEL_ID = 'sentence-transformers/all-MiniLM-L6-v2'
DEFAULT_MODEL_REVISION = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'


@dataclass(frozen=True)
class EmbeddingConfig:
    model_id: str = DEFAULT_MODEL_ID
    revision: str = DEFAULT_MODEL_REVISION
    chunk_tokens: int = 180
    overlap_tokens: int = 30

    def __post_init__(self):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', self.model_id):
            raise ValueError('EMBEDDING_MODEL_ID must be a Hugging Face owner/model ID.')
        if not re.fullmatch(r'[a-f0-9]{40}', self.revision):
            raise ValueError('EMBEDDING_MODEL_REVISION must pin a full 40-character commit SHA.')
        if not 0 <= self.overlap_tokens < self.chunk_tokens <= 240:
            raise ValueError('Require 0 <= CHUNK_OVERLAP_TOKENS < CHUNK_TOKENS <= 240.')

    @classmethod
    def from_env(cls):
        model_id = os.getenv('EMBEDDING_MODEL_ID', DEFAULT_MODEL_ID)
        revision = os.getenv('EMBEDDING_MODEL_REVISION', '')
        if model_id != DEFAULT_MODEL_ID and not revision:
            raise ValueError('A custom embedding model requires an explicit pinned revision.')
        return cls(model_id, revision or DEFAULT_MODEL_REVISION,
                   int(os.getenv('CHUNK_TOKENS', '180')),
                   int(os.getenv('CHUNK_OVERLAP_TOKENS', '30')))
