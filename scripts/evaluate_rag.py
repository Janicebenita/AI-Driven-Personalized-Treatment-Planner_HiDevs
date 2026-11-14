"""Real embedding retrieval checks, without a provider credential or patient data."""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.retrieval import KnowledgeBase

CASES = [
    ('SLCO1B1 poor function simvastatin myopathy muscle toxicity', 'CPIC-STATIN'),
    ('chronic kidney disease eGFR 25 diabetes renal metformin pathway', 'NG28-RENAL'),
    ('SGLT2 fasting surgery critical illness ketosis advice', 'KDIGO-2024'),
    ('individual preferences diet lifestyle HbA1c follow up interval', 'NG28-CARE'),
    ('insulin sulfonylurea hypoglycaemia review adverse effects', 'NG28-REVIEW'),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', choices=['chroma', 'faiss'], default='chroma')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    kb = KnowledgeBase(backend=args.backend, allow_fallback=False)
    setup_ms = round((time.perf_counter() - started) * 1000, 2)
    rows = []
    for query, expected in CASES:
        start = time.perf_counter()
        matches = kb.search(query, 3)
        source_ids = [m['source_id'] for m in matches]
        rows.append({'query': query, 'expected': expected, 'retrieved': source_ids,
                     'hit_at_3': expected in source_ids,
                     'elapsed_ms': round((time.perf_counter() - start) * 1000, 2)})
    result = {'model': kb.model_id,
              'model_revision': kb.model_revision, 'backend': kb.backend,
              'corpus_sha256': kb.fingerprint, 'chunks': len(kb.chunks),
              'setup_ms': setup_ms, 'hit_at_3': sum(r['hit_at_3'] for r in rows) / len(rows),
              'cases': rows,
              'limitation': 'Five small developer-authored retrieval checks; not a clinical or generation-quality evaluation.'}
    print(json.dumps(result, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return 0 if all(row['hit_at_3'] for row in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
