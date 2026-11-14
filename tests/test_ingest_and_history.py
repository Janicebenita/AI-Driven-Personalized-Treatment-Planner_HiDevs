import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from rag.history import load_synthetic_history, save_synthetic_history
from rag.ingest import main
from rag.ingestion import ROOT


class IngestAndHistoryTests(unittest.TestCase):
    def test_ingestion_cli_produces_unreviewed_provenance_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'evidence.txt', Path(directory) / 'draft.json'
            source.write_text('Public document\n\nReviewed later.', encoding='utf-8')
            argv = ['ingest', str(source), '--source-id', 'TEST', '--source-url',
                    'https://publisher.example/guide', '--output', str(output)]
            with patch.object(sys, 'argv', argv):
                main()
            draft = json.loads(output.read_text())
            self.assertEqual(draft['review_status'], 'unreviewed')
            self.assertEqual(draft['pages'][0]['page'], 1)
            self.assertEqual(draft['source_url'], 'https://publisher.example/guide')
            with patch.object(sys, 'argv', argv), self.assertRaises(SystemExit):
                main()  # A repeat cannot overwrite an existing review draft.

    def test_ingestion_cli_rejects_non_https_provenance(self):
        with patch.object(sys, 'argv', ['ingest', 'ignored.txt', '--source-id', 'TEST',
                '--source-url', 'http://untrusted.example', '--output', 'unused.json']):
            with self.assertRaises(SystemExit):
                main()

    def test_model_build_cache_honors_the_pinned_configuration(self):
        downloader = MagicMock()
        with patch.dict(sys.modules, {'huggingface_hub': SimpleNamespace(snapshot_download=downloader)}):
            runpy.run_path(str(ROOT / 'deploy/cache_model.py'))
        self.assertEqual(len(downloader.call_args.kwargs['revision']), 40)
        self.assertNotIn('token', downloader.call_args.kwargs)

    def test_history_is_session_scoped_expiring_and_opt_in(self):
        collection = MagicMock()
        collection.insert_one.return_value.inserted_id = 'synthetic-record'
        client = MagicMock()
        client.__enter__.return_value.__getitem__.return_value.__getitem__.return_value = collection
        mongo = SimpleNamespace(MongoClient=MagicMock(return_value=client))
        errors = SimpleNamespace(PyMongoError=type('FakeMongoError', (Exception,), {}))
        with patch.dict(sys.modules, {'pymongo': mongo, 'pymongo.errors': errors}):
            self.assertEqual(save_synthetic_history({'status': 'review-required'}, 'session-a', True,
                                                   'mongodb://synthetic'), 'synthetic-record')
            saved = collection.insert_one.call_args.args[0]
            self.assertEqual(saved['session_id'], 'session-a')
            self.assertTrue(saved['synthetic_only'])
            self.assertEqual((saved['expires_at'] - saved['created_at']).days, 7)
            collection.create_index.assert_called_once_with('expires_at', expireAfterSeconds=0)
            load_synthetic_history('session-a', 'mongodb://synthetic')
            query = collection.find.call_args.args[0]
            self.assertEqual(query['session_id'], 'session-a')
            self.assertIn('$gt', query['expires_at'])
        self.assertEqual(load_synthetic_history('', ''), [])

    def test_database_errors_do_not_expose_credentials(self):
        error = type('FakeMongoError', (Exception,), {})
        client = MagicMock(side_effect=error('mongodb://secret-password'))
        with patch.dict(sys.modules, {'pymongo': SimpleNamespace(MongoClient=client),
                                     'pymongo.errors': SimpleNamespace(PyMongoError=error)}):
            for function, args in [(save_synthetic_history, ({}, 'session', True, 'mongodb://secret')),
                                   (load_synthetic_history, ('session', 'mongodb://secret'))]:
                with self.assertRaises(RuntimeError) as caught:
                    function(*args)
                self.assertNotIn('secret', str(caught.exception))
        with self.assertRaises(ValueError):
            save_synthetic_history({}, '', True, '')
