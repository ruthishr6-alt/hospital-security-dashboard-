from database.db import query_db, execute_db

class AuditService:
    """Tamper-evident audit logging for all cybersecurity and clinical actions."""

    @classmethod
    def log(cls, user_id, role, action, patient_id=None, ip_address='127.0.0.1',
            device_status='UNKNOWN', risk_score=10, risk_level='LOW',
            result='SUCCESS', threat_type=None, session_id=None, details=''):
        """Inserts an immutable audit record."""
        return execute_db('''
            INSERT INTO audit_logs (
                timestamp, user_id, role, patient_id, action, ip_address,
                device_status, risk_score, risk_level, result, threat_type,
                session_id, details
            ) VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id or 'UNKNOWN', role or 'unauthenticated', patient_id, action,
              ip_address, device_status, risk_score, risk_level, result,
              threat_type, session_id, details))

    @classmethod
    def get_logs(cls, limit=100, offset=0, user_filter=None, patient_filter=None,
                 threat_filter=None, action_filter=None, result_filter=None):
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if user_filter:
            query += " AND user_id LIKE ?"
            params.append(f"%{user_filter}%")
        if patient_filter:
            query += " AND patient_id = ?"
            params.append(patient_filter)
        if threat_filter:
            query += " AND risk_level = ?"
            params.append(threat_filter)
        if action_filter:
            query += " AND action = ?"
            params.append(action_filter)
        if result_filter:
            query += " AND result = ?"
            params.append(result_filter)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return query_db(query, params)

    @classmethod
    def get_summary_stats(cls):
        total = query_db("SELECT COUNT(*) as cnt FROM audit_logs", one=True)['cnt']
        success = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE result = 'SUCCESS'", one=True)['cnt']
        blocked = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE result = 'DENIED'", one=True)['cnt']
        decoy = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE result = 'DECOY_SERVED'", one=True)['cnt']
        failed_logins = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE action = 'LOGIN_FAILED'", one=True)['cnt']

        return {
            'total_audits': total,
            'success_count': success,
            'blocked_count': blocked,
            'decoy_count': decoy,
            'failed_logins_count': failed_logins
        }
