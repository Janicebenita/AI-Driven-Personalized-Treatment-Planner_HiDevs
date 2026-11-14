"""Extract a supplied local public document to a provenance-preserving review draft."""
import argparse
import json
from pathlib import Path

from .ingestion import extract_local_document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--source-url', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.source_url.startswith('https://'):
        parser.error('Source URL must use HTTPS.')
    if args.output.exists():
        parser.error('Output already exists. Choose a new review-draft path.')
    pages = extract_local_document(args.path)
    draft = {'source_id': args.source_id, 'source_url': args.source_url,
             'review_status': 'unreviewed', 'pages': pages,
             'next_step': 'Review extracted text, provenance and rights; create approved section records before adding to data/evidence.json.'}
    args.output.write_text(json.dumps(draft, indent=2), encoding='utf-8')
    print(f'Extracted {len(pages)} page(s) to a review draft. No vector index was modified.')


if __name__ == '__main__':
    main()
