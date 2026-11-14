"""Local MiniLM embeddings, Chroma persistence, explicit FAISS compatibility fallback."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from .config import EmbeddingConfig
from .ingestion import ROOT, chunk_corpus, load_corpus


class KnowledgeBase:
    def __init__(self, directory: Path | None = None, backend: str = 'chroma',
                 allow_fallback: bool = True, config: EmbeddingConfig | None = None):
        if backend not in ('chroma', 'faiss'):
            raise ValueError('VECTOR_BACKEND must be chroma or faiss.')
        self.config = config or EmbeddingConfig.from_env()
        self.model_id = self.config.model_id
        from huggingface_hub import snapshot_download
        from huggingface_hub.errors import LocalEntryNotFoundError
        from sentence_transformers import SentenceTransformer
        try:
            snapshot = snapshot_download(self.model_id, revision=self.config.revision, local_files_only=True)
        except LocalEntryNotFoundError:
            snapshot = snapshot_download(self.model_id, revision=self.config.revision,
                allow_patterns=['*.json', '*.safetensors', 'vocab.txt', 'tokenizer.*',
                                '*.txt', '1_Pooling/*'])
        # Load from a pinned local snapshot, avoiding remote template/metadata lookups on reruns.
        self.encoder = SentenceTransformer(snapshot, local_files_only=True,
                                           device='cpu', trust_remote_code=False)
        if self.config.chunk_tokens + 2 > self.encoder.max_seq_length:
            raise ValueError('CHUNK_TOKENS exceeds the selected embedding model context length.')
        self.records = load_corpus()
        self.chunks = chunk_corpus(self.records, self.encoder.tokenizer,
                                   self.config.chunk_tokens, self.config.overlap_tokens)
        self.model_revision = self.config.revision
        fingerprint = hashlib.sha256(json.dumps({
            'model': self.model_id, 'revision': self.model_revision, 'version': 1,
            'chunks': self.chunks}, sort_keys=True).encode()).hexdigest()
        self.fingerprint = fingerprint
        directory = directory or ROOT / '.careweave' / 'vectors'
        self.directory = Path(directory) / fingerprint[:20]
        self.directory.mkdir(parents=True, exist_ok=True)
        self.backend, self.fallback_reason = backend, None
        # Cache only public evidence embeddings, never patient/query data.
        import numpy as np
        cached = self.directory / 'embeddings.npy'
        if cached.exists():
            vectors = np.load(cached, allow_pickle=False)
            if vectors.shape != (len(self.chunks), self.encoder.get_sentence_embedding_dimension()):
                raise ValueError('Cached embedding shape does not match the corpus.')
        else:
            vectors = self.encoder.encode([c['text'] for c in self.chunks],
                                          normalize_embeddings=True, show_progress_bar=False)
            with tempfile.NamedTemporaryFile(dir=self.directory, suffix='.npy', delete=False) as handle:
                temporary = Path(handle.name)
                np.save(handle, vectors, allow_pickle=False)
            temporary.replace(cached)
        self.vectors = np.asarray(vectors, dtype='float32')
        if backend == 'chroma':
            try:
                import chromadb
                from chromadb.config import Settings
                self.client = chromadb.PersistentClient(str(self.directory / 'chroma'),
                                                        settings=Settings(anonymized_telemetry=False))
                self.collection = self.client.get_or_create_collection(
                    name='careweave-' + fingerprint[:20], metadata={'hnsw:space': 'cosine'},
                    embedding_function=None)
                if self.collection.count() != len(self.chunks):
                    self.collection.upsert(ids=[c['id'] for c in self.chunks],
                                           documents=[c['text'] for c in self.chunks],
                                           metadatas=[c['metadata'] for c in self.chunks],
                                           embeddings=self.vectors.tolist())
            except (ImportError, OSError, RuntimeError) as exc:
                if not allow_fallback:
                    raise RuntimeError('Chroma initialization failed; review compatibility before enabling FAISS.') from exc
                self.fallback_reason = f'Chroma unavailable ({type(exc).__name__}); using FAISS.'
                self.backend = 'faiss'
        if self.backend == 'faiss':
            try:
                import faiss
            except ImportError as exc:
                raise RuntimeError('FAISS fallback requires: pip install -r requirements-faiss.txt') from exc
            self.index = faiss.IndexFlatIP(self.vectors.shape[1])
            self.index.add(self.vectors)
            faiss.write_index(self.index, str(self.directory / 'evidence.faiss'))
        (self.directory / 'manifest.json').write_text(json.dumps({
            'model': self.model_id, 'model_revision': self.model_revision,
            'corpus_sha256': fingerprint, 'backend': self.backend,
            'chunks': self.chunks}, indent=2), encoding='utf-8')

    def search(self, query: str, limit: int = 4) -> list[dict]:
        if not isinstance(query, str) or not query.strip() or len(query) > 8000:
            raise ValueError('Query must contain 1–8000 characters.')
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError('Retrieval limit must be a positive integer.')
        count = min(limit, len(self.chunks))
        # Embed all query windows, rather than silently truncating a long patient context.
        import numpy as np
        offsets = self.encoder.tokenizer(query, add_special_tokens=False,
                                         return_offsets_mapping=True)['offset_mapping']
        if not offsets:
            raise ValueError('Query has no encodable tokens.')
        window = getattr(self, 'config', EmbeddingConfig()).chunk_tokens
        parts = [query[offsets[i][0]:offsets[min(i + window, len(offsets)) - 1][1]]
                 for i in range(0, len(offsets), window)]
        encoded = self.encoder.encode(parts, normalize_embeddings=True, show_progress_bar=False)
        vector = encoded.mean(axis=0, keepdims=True)
        norm = float(np.linalg.norm(vector))
        if norm <= 0 or not np.isfinite(norm):
            raise ValueError('Query embedding is invalid.')
        vector = vector / norm
        if self.backend == 'chroma':
            result = self.collection.query(query_embeddings=vector.tolist(), n_results=count,
                                           include=['documents', 'metadatas', 'distances'])
            return [{'chunk_id': cid, 'text': text, **metadata,
                     'cosine_similarity': round(1 - float(distance), 6)}
                    for cid, text, metadata, distance in zip(
                        result['ids'][0], result['documents'][0], result['metadatas'][0], result['distances'][0])]
        scores, positions = self.index.search(vector.astype('float32'), count)
        return [{'chunk_id': self.chunks[int(i)]['id'], 'text': self.chunks[int(i)]['text'],
                 **self.chunks[int(i)]['metadata'], 'cosine_similarity': round(float(score), 6)}
                for score, i in zip(scores[0], positions[0]) if i >= 0]
