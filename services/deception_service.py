import json
import uuid
from datetime import datetime
from database.db import query_db, execute_db

class DeceptionService:
    """
    Orchestrates the isolated Honeypot / Decoy environment.
    Serves exclusively synthetic decoy patient records and records adversary interaction telemetry.
    """

    @classmethod
    def get_decoy_patient(cls, patient_id=None):
        """
        Retrieves a decoy patient from decoy_patients.
        If patient_id requested, searches for it; otherwise serves default canary.
        """
        if patient_id:
            row = query_db("SELECT * FROM decoy_patients WHERE patient_id = ?", (patient_id,), one=True)
            if row:
                return cls._format_decoy(row)

        # Default flagship canary
        row = query_db("SELECT * FROM decoy_patients WHERE patient_id = 'HP-DEC-101'", one=True)
        if row:
            return cls._format_decoy(row)

        row = query_db("SELECT * FROM decoy_patients LIMIT 1", one=True)
        return cls._format_decoy(row) if row else None

    @classmethod
    def get_all_decoy_patients(cls):
        rows = query_db("SELECT * FROM decoy_patients ORDER BY patient_id ASC")
        return [cls._format_decoy(r) for r in rows]

    @classmethod
    def record_decoy_interaction(cls, user_id, ip_address, fake_patient_id, action_performed, risk_score, threat_level):
        """Logs adversary interaction in decoy_sessions table."""
        session_id = f"SESS-DEC-{uuid.uuid4().hex[:8].upper()}"
        execute_db('''
            INSERT INTO decoy_sessions (
                decoy_session_id, user_id, ip_address, timestamp,
                fake_patient_searched, fake_record_viewed, actions_performed,
                request_count, risk_score, threat_level
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, 1, ?, ?)
        ''', (session_id, user_id or 'UNKNOWN', ip_address, fake_patient_id or 'GENERAL', fake_patient_id or 'GENERAL', action_performed, risk_score, threat_level))
        return session_id

    @classmethod
    def get_decoy_sessions(cls, limit=50):
        return query_db("SELECT * FROM decoy_sessions ORDER BY timestamp DESC LIMIT ?", (limit,))

    @classmethod
    def get_stats(cls):
        total = query_db("SELECT COUNT(*) as cnt FROM decoy_sessions", one=True)['cnt']
        canaries_count = query_db("SELECT COUNT(*) as cnt FROM decoy_patients", one=True)['cnt']
        return {
            'total_decoy_sessions': total,
            'total_canaries': canaries_count
        }

    @staticmethod
    def _format_decoy(row):
        if not row:
            return None
        d = dict(row)
        for key in ['vitals', 'current_prescriptions']:
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        d['is_decoy'] = 1
        d['banner_notice'] = "SECURITY MONITORING MODE – SYNTHETIC DECOY DATA"
        return d
