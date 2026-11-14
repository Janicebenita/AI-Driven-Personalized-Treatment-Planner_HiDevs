"""Optional explicit-opt-in synthetic history. No automatic conversation retention."""
from datetime import UTC, datetime, timedelta


def save_synthetic_history(report: dict, session_id: str, consent: bool, uri: str,
                           database: str = 'careweave') -> str:
    if not consent:
        raise ValueError('Explicit synthetic-history consent is required.')
    if not uri or not session_id:
        raise ValueError('MongoDB URI and session ID are required.')
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    try:
        with MongoClient(uri, serverSelectionTimeoutMS=4000) as client:
            collection = client[database]['synthetic_reports']
            collection.create_index('expires_at', expireAfterSeconds=0)
            now = datetime.now(UTC)
            result = collection.insert_one({'session_id': session_id, 'created_at': now,
                'expires_at': now + timedelta(days=7), 'synthetic_only': True, 'report': report})
            return str(result.inserted_id)
    except PyMongoError as exc:
        raise RuntimeError('Synthetic history is unavailable; check database connectivity and access.') from exc


def load_synthetic_history(session_id: str, uri: str, database: str = 'careweave') -> list:
    if not session_id or not uri:
        return []
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    try:
        with MongoClient(uri, serverSelectionTimeoutMS=4000) as client:
            return list(client[database]['synthetic_reports'].find(
                {'session_id': session_id, 'expires_at': {'$gt': datetime.now(UTC)}},
                {'_id': 0, 'report': 1, 'created_at': 1}).sort('created_at', -1).limit(10))
    except PyMongoError as exc:
        raise RuntimeError('Synthetic history is unavailable; check database connectivity and access.') from exc
