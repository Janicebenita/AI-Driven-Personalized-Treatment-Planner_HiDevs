"""Opt-in integration tests run actual model + tokenizer + Chroma + Node; only provider I/O is mocked."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rag.config import EmbeddingConfig
from rag.ingestion import ROOT
from rag.pipeline import create_report


@unittest.skipUnless(os.getenv('CAREWEAVE_RUN_SEMANTIC_TESTS') == '1',
                     'Set CAREWEAVE_RUN_SEMANTIC_TESTS=1 to run real embedding integration.')
class SemanticIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rag.retrieval import KnowledgeBase
        cls.directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.kb = KnowledgeBase(Path(cls.directory.name), allow_fallback=False, config=EmbeddingConfig())
        cls.profile = json.loads((ROOT / 'data/synthetic-cases.json').read_text())['renal']

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_actual_patient_to_retrieval_to_review_report(self):
        report = create_report(self.profile, self.kb)
        self.assertEqual(report['mode'], 'semantic-retrieval-only')
        self.assertEqual(report['retrieval']['backend'], 'chroma')
        self.assertTrue(report['retrieval']['matches'])
        ids = {e['id'] for e in report['evidence']}
        for field in ['options', 'monitoring']:
            self.assertTrue(all(item['source'] in ids for item in report[field]))
        self.assertTrue(any(r['source'] == 'CPIC-STATIN' for r in report['risks']))
        self.assertTrue(report['missing'])

    def test_real_renal_counterfactual_changes_the_plan(self):
        report = create_report({**self.profile, 'egfr': 24}, self.kb)
        self.assertIn('kidney-specific', report['options'][0]['title'])
        self.assertTrue(any(r['title'].startswith('Metformin needs') for r in report['risks']))

    def test_real_retrieval_context_to_validated_provider_briefing(self):
        def reply(request, timeout):
            context = json.loads(json.loads(request.data)['messages'][1]['content'])
            self.assertIn('NG28-RENAL', {e['id'] for e in context['evidence']})
            self.assertTrue(context['risks'])
            text = json.dumps({'summary': 'Discuss the renal pathway with the clinician.',
                'uncertainty': 'Renal trend and full medication review remain missing.',
                'sourceIds': ['NG28-RENAL']})
            return io.BytesIO(json.dumps({'choices': [{'finish_reason': 'stop',
                                                       'message': {'content': text}}]}).encode())
        with patch.dict(os.environ, {'GROQ_API_KEY': 'synthetic-test-key'}), \
             patch('urllib.request.urlopen', side_effect=reply):
            report = create_report(self.profile, self.kb, True)
        self.assertEqual(report['mode'], 'groq-ai-assisted')
        self.assertTrue(report['ai'])
        self.assertTrue(any(r['source'] == 'CPIC-STATIN' for r in report['risks']))

    def test_actual_safety_gate_prevents_retrieval(self):
        with patch.object(self.kb, 'search', side_effect=AssertionError('Must not query')):
            report = create_report({**self.profile, 'acute': True}, self.kb, True)
        self.assertEqual(report['status'], 'withheld')
        self.assertIsNone(report['ai'])

    def test_cached_document_vectors_and_index_have_stable_identity(self):
        import chromadb
        from chromadb.config import Settings
        self.assertTrue((self.kb.directory / 'embeddings.npy').exists())
        manifest = json.loads((self.kb.directory / 'manifest.json').read_text())
        self.assertEqual(manifest['corpus_sha256'], self.kb.fingerprint)
        reopened = chromadb.PersistentClient(str(self.kb.directory / 'chroma'),
                                             settings=Settings(anonymized_telemetry=False))
        self.assertEqual(reopened.get_collection('careweave-' + self.kb.fingerprint[:20]).count(),
                         len(self.kb.chunks))
