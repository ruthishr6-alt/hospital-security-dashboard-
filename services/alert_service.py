from database.db import query_db, execute_db

class AlertService:
    """Manages cybersecurity alerts lifecycle."""

    @classmethod
    def get_all_alerts(cls, status_filter=None, severity_filter=None):
        query = "SELECT * FROM security_alerts WHERE 1=1"
        params = []
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        if severity_filter:
            query += " AND severity = ?"
            params.append(severity_filter)
        query += " ORDER BY timestamp DESC"
        return query_db(query, params)

    @classmethod
    def update_alert_status(cls, alert_id, new_status):
        execute_db('''
            UPDATE security_alerts
            SET status = ?
            WHERE alert_id = ?
        ''', (new_status, alert_id))
