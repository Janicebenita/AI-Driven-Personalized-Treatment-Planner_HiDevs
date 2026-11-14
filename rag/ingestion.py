"""Source-aware preprocessing and bounded token chunking; no uncontrolled web crawling."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ('id', 'title', 'url', 'section', 'summary', 'publisher', 'year')


def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKC', text).replace('\x00', '')
    text = re.sub(r'[ \t]+', ' ', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def load_corpus(path: Path = ROOT / 'data/evidence.json') -> list[dict]:
    records = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(records, list) or not records:
        raise ValueError('Evidence corpus must be a non-empty JSON array.')
    result, ids = [], {}
    for record in records:
        if not isinstance(record, dict) or any(not str(record.get(k, '')).strip() for k in REQUIRED):
            raise ValueError('Evidence record is missing required provenance or content.')
        if not record['url'].startswith('https://'):
            raise ValueError('Source URL must use HTTPS.')
        if record.get('review_status') not in ('prototype-curated', 'approved-for-prototype'):
            raise ValueError('Unreviewed documents cannot enter the retrieval corpus.')
        clean = {**record, 'summary': normalize(record['summary'])}
        if not clean['summary']:
            raise ValueError('Evidence text is empty after normalization.')
        digest = hashlib.sha256((record['id'] + clean['summary']).encode()).hexdigest()
        signature = json.dumps(clean, sort_keys=True)
        if record['id'] in ids:
            if ids[record['id']] == signature:
                continue  # Identical repeated record; preserve different-source corroboration.
            raise ValueError('Conflicting records use the same evidence ID.')
        ids[record['id']] = signature
        result.append({**clean, 'content_sha256': digest})
    return result


def extract_local_document(path: Path) -> list[dict]:
    """Offline extraction for an explicitly supplied public document; review before indexing."""
    if path.stat().st_size > 20_000_000:
        raise ValueError('Document exceeds the 20 MB ingestion limit.')
    if path.suffix.lower() in ('.txt', '.md'):
        return [{'page': 1, 'text': normalize(path.read_text(encoding='utf-8'))}]
    if path.suffix.lower() == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(path)
        if len(reader.pages) > 500:
            raise ValueError('PDF exceeds the 500-page ingestion limit.')
        return [{'page': i + 1, 'text': normalize(page.extract_text() or '')}
                for i, page in enumerate(reader.pages)]
    raise ValueError('Supported offline formats are PDF, Markdown and UTF-8 text.')


def chunk_corpus(records: list[dict], tokenizer, max_tokens: int = 180,
                 overlap: int = 30) -> list[dict]:
    if not 0 <= overlap < max_tokens <= 240:
        raise ValueError('Require 0 <= overlap < max_tokens <= 240.')
    chunks = []
    for record in records:
        # Keep provenance outside the embedded body so metadata cannot silently consume token budget.
        text = record['summary']
        offsets = tokenizer(text, add_special_tokens=False,
                            return_offsets_mapping=True)['offset_mapping']
        start = 0
        while start < len(offsets):
            end = min(start + max_tokens, len(offsets))
            body = text[offsets[start][0]:offsets[end - 1][1]]
            digest = hashlib.sha256(body.encode()).hexdigest()
            chunks.append({'id': f"{record['id']}:{start}:{digest[:12]}",
                           'text': body, 'metadata': {
                               'source_id': record['id'], 'title': record['title'],
                               'url': record['url'], 'section': record['section'],
                               'publisher': record['publisher'], 'year': str(record['year']),
                               'token_start': start, 'token_end': end,
                               'content_sha256': digest,
                               'retrieved_at': record.get('retrieved_at', 'unknown')}})
            if end == len(offsets):
                break
            start = end - overlap
    if not chunks:
        raise ValueError('No text chunks were produced.')
    return chunks
