import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from rag.config import DEFAULT_MODEL_ID, DEFAULT_MODEL_REVISION, EmbeddingConfig
from rag.errors import ProviderError
from rag.ingestion import load_corpus
from rag.pipeline import create_report, groq_briefing, safety_plan


class ConfigAndFailureTests(unittest.TestCase):
    def test_defaults_and_explicit_pinned_override(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(EmbeddingConfig.from_env().revision, DEFAULT_MODEL_REVISION)
        with patch.dict(os.environ, {'EMBEDDING_MODEL_ID': 'example/custom-model',
                'EMBEDDING_MODEL_REVISION': 'a' * 40, 'CHUNK_TOKENS': '120',
                'CHUNK_OVERLAP_TOKENS': '20'}, clear=True):
            config = EmbeddingConfig.from_env()
        self.assertEqual(config.model_id, 'example/custom-model')
        self.assertEqual(config.chunk_tokens, 120)

    def test_invalid_configuration_cannot_download_an_unpinned_model(self):
        for env in [{'EMBEDDING_MODEL_ID': 'example/new'},
                    {'EMBEDDING_MODEL_ID': '../../local-path'},
                    {'EMBEDDING_MODEL_REVISION': 'main'},
                    {'CHUNK_TOKENS': 'no'}, {'CHUNK_TOKENS': '241'},
                    {'CHUNK_TOKENS': '30', 'CHUNK_OVERLAP_TOKENS': '30'}]:
            with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
                EmbeddingConfig.from_env()

    def test_missing_provider_is_distinct_from_invalid_output(self):
        with self.assertRaises(ProviderError) as caught:
            groq_briefing({}, '', 'model')
        self.assertEqual(caught.exception.code, 'not_configured')

    def test_provider_http_errors_are_safe_and_actionable(self):
        for status, code in [(401, 'authentication'), (403, 'authentication'),
                             (429, 'rate_limit'), (503, 'provider_http')]:
            def fail(*args, **kwargs):
                raise HTTPError('https://api.groq.com/openai/v1/chat/completions', status,
                                'sensitive upstream body must not surface', {}, None)
            with self.assertRaises(ProviderError) as caught:
                groq_briefing({}, 'secret-test-key', 'model', fail)
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn('secret-test-key', str(caught.exception))
            self.assertNotIn('sensitive upstream', str(caught.exception))

    def test_connection_failure_and_timeout_are_classified(self):
        for failure in [URLError('offline'), TimeoutError('timeout')]:
            with self.assertRaises(ProviderError) as caught:
                groq_briefing({}, 'test-key', 'model', lambda *a, **k: (_ for _ in ()).throw(failure))
            self.assertEqual(caught.exception.code, 'network')

    def test_malformed_and_truncated_provider_responses_fail_closed(self):
        values = [b'not-json', b'\xff', b'[]', b'{}',
            json.dumps({'choices': [None]}).encode(),
            json.dumps({'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]}).encode(),
            json.dumps({'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}).encode()]
        for raw in values:
            with self.assertRaises(ProviderError) as caught:
                groq_briefing({'evidence': []}, 'test', 'model', lambda *a, **k: io.BytesIO(raw))
            self.assertEqual(caught.exception.code, 'invalid_response')

    def test_provider_failure_preserves_safety_report_and_safe_log(self):
        from rag.ingestion import ROOT
        profile = json.loads((ROOT / 'data/synthetic-cases.json').read_text())['renal']
        class KB:
            records = load_corpus()
            backend, fingerprint, fallback_reason, model_id = 'test', 'test', None, DEFAULT_MODEL_ID
            def search(self, query):
                return [{'source_id': 'NG28-RENAL'}]
        with patch('rag.pipeline.groq_briefing', side_effect=ProviderError('rate_limit', 'Retry later.')):
            with self.assertLogs('rag.pipeline', level='WARNING') as logs:
                report = create_report(profile, KB(), True)
        self.assertEqual(report['aiErrorCode'], 'rate_limit')
        self.assertEqual(report['mode'], 'semantic-retrieval-only')
        self.assertTrue(any(r['source'] == 'CPIC-STATIN' for r in report['risks']))
        self.assertIn('code=rate_limit', logs.output[0])
        self.assertNotIn(profile['goal'], logs.output[0])

    def test_bad_patient_profile_fails_at_shared_safety_boundary(self):
        with self.assertRaises(ValueError):
            safety_plan({'age': 'invalid'})

    def test_empty_or_non_https_corpus_is_rejected(self):
        record = load_corpus()[0]
        for data in [[], {}, [{**record, 'url': 'http://untrusted.example'}],
                     [{**record, 'summary': '\x00 \t'}]]:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'corpus.json'
                path.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_corpus(path)
