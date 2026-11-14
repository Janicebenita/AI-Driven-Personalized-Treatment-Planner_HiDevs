import copy
import io
import json
import re
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rag.ingestion import ROOT, chunk_corpus, extract_local_document, load_corpus, normalize
from rag.pipeline import create_report, groq_briefing, safety_plan, validate_briefing
from rag.history import save_synthetic_history


class WordTokenizer:
    def __call__(self, text, **kwargs):
        return {'offset_mapping': [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.records = load_corpus()
        self.profile = json.loads((ROOT / 'data/synthetic-cases.json').read_text())['renal']

    def test_normalize_preserves_paragraph_context(self):
        self.assertEqual(normalize('Ａ\x00  B\n\n\nC'), 'A B\n\nC')

    def test_chunks_obey_budget_overlap_and_provenance(self):
        records = copy.deepcopy(self.records[:1])
        records[0]['summary'] = ' '.join(f'w{i}' for i in range(400))
        chunks = chunk_corpus(records, WordTokenizer(), max_tokens=180, overlap=30)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[1]['metadata']['token_start'], 150)
        for chunk in chunks:
            self.assertLessEqual(len(chunk['text'].split()), 180)
            self.assertEqual(chunk['metadata']['source_id'], records[0]['id'])
            self.assertTrue(chunk['metadata']['content_sha256'])
        self.assertEqual(chunks, chunk_corpus(records, WordTokenizer()))

    def test_invalid_chunk_parameters_fail(self):
        for maximum, overlap in [(20, 20), (250, 20), (180, -1)]:
            with self.assertRaises(ValueError):
                chunk_corpus(self.records, WordTokenizer(), maximum, overlap)

    def test_unreviewed_duplicate_and_incomplete_sources_rejected(self):
        for transform in [lambda r: [{**r[0], 'review_status': 'unreviewed'}],
                          lambda r: [r[0], {**r[0], 'summary': 'Conflicting content'}], lambda r: [{**r[0], 'url': ''}]]:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'bad.json'
                path.write_text(json.dumps(transform(self.records)), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_corpus(path)

    def test_identical_records_are_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'repeated.json'
            path.write_text(json.dumps([self.records[0], self.records[0]]), encoding='utf-8')
            self.assertEqual(len(load_corpus(path)), 1)

    def test_plain_document_extraction_and_format_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'section.md'
            path.write_text('# Kidney\n\nReviewed public evidence.', encoding='utf-8')
            self.assertEqual(extract_local_document(path)[0]['page'], 1)
            path = Path(directory) / 'unsupported.exe'
            path.write_text('not a document')
            with self.assertRaises(ValueError):
                extract_local_document(path)

    def test_shared_safety_core_does_not_diverge(self):
        report = safety_plan(self.profile)
        self.assertTrue(any(r['source'] == 'CPIC-STATIN' for r in report['risks']))
        self.assertEqual(report['status'], 'review-required')

    def test_withheld_case_never_retrieves_or_generates(self):
        class NoRetrieval:
            def search(self, *_):
                raise AssertionError('Retrieval must not execute')
        with patch('rag.pipeline.groq_briefing', side_effect=AssertionError('No provider')):
            report = create_report({**self.profile, 'acute': True}, NoRetrieval(), True)
        self.assertEqual(report['status'], 'withheld')
        self.assertEqual(report['options'], [])

    def test_semantic_retrieval_retains_rule_sources(self):
        records = self.records
        class KB:
            backend, fallback_reason, fingerprint = 'chroma', None, 'test-corpus'
            def search(self, query):
                return [{'source_id': 'NG28-CARE', 'cosine_similarity': 0.5}]
        kb = KB()
        kb.records = records
        report = create_report(self.profile, kb)
        self.assertEqual(report['mode'], 'semantic-retrieval-only')
        self.assertIn('CPIC-STATIN', [e['id'] for e in report['evidence']])
        self.assertIn('MiniLM', report['trace'][2]['detail'])

    def test_invalid_provider_citations_and_empty_fields_rejected(self):
        valid = {'summary': 'Review renal context.', 'uncertainty': 'Renal trend unknown.', 'sourceIds': ['NG28-RENAL']}
        for invalid in [{**valid, 'sourceIds': ['invented']}, {**valid, 'sourceIds': []},
                        {**valid, 'summary': ''}, {**valid, 'extra': 'no'}, []]:
            with self.assertRaises(ValueError):
                validate_briefing(invalid, {'NG28-RENAL'})

    def test_groq_request_contract_and_result_validation(self):
        answer = {'summary': 'Review with a clinician.', 'uncertainty': 'Renal trend is missing.', 'sourceIds': ['NG28-RENAL']}
        def opener(request, timeout):
            self.assertEqual(request.full_url, 'https://api.groq.com/openai/v1/chat/completions')
            payload = json.loads(request.data)
            self.assertEqual(payload['response_format']['type'], 'json_object')
            self.assertIn('untrusted', payload['messages'][0]['content'])
            return io.BytesIO(json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(answer)}}]}).encode())
        self.assertEqual(groq_briefing({'evidence': [{'id': 'NG28-RENAL'}]}, 'synthetic', 'llama-test', opener), answer)

    def test_history_requires_opt_in_before_database_import_or_write(self):
        with self.assertRaises(ValueError):
            save_synthetic_history({}, 'test-session', False, 'mongodb://not-contacted')

    @unittest.skipUnless(importlib.util.find_spec('numpy'), 'NumPy is needed for embedding-window checks.')
    def test_long_queries_are_windowed_and_renormalized(self):
        import numpy as np
        from rag.retrieval import KnowledgeBase
        class Encoder:
            tokenizer = WordTokenizer()
            def encode(inner, parts, **kwargs):
                self.assertEqual(len(parts), 2)
                self.assertTrue(all(len(p.split()) <= 180 for p in parts))
                return np.array([[1.0, 0.0], [0.0, 1.0]], dtype='float32')
        class Collection:
            def query(inner, query_embeddings, **kwargs):
                self.assertAlmostEqual(float(np.linalg.norm(query_embeddings[0])), 1.0, places=6)
                self.assertGreater(query_embeddings[0][1], 0.7)
                return {'ids': [['test']], 'documents': [['test']],
                        'metadatas': [[{'source_id': 'TEST'}]], 'distances': [[0.0]]}
        kb = KnowledgeBase.__new__(KnowledgeBase)
        kb.encoder, kb.collection, kb.backend, kb.chunks = Encoder(), Collection(), 'chroma', [{}]
        self.assertEqual(kb.search(' '.join(['word'] * 181), 1)[0]['source_id'], 'TEST')


if __name__ == '__main__':
    unittest.main()
