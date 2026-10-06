import uuid
from datetime import datetime
from database.db import query_db, execute_db

class ThreatDetector:
    """
    Evaluates cybersecurity patterns, detects insider threats,
    and logs structured security alerts for SOC review.
    """

    @classmethod
    def analyze_event(cls, user_id, action, risk_score, details, threat_type=None, severity=None):
        """
        Generates a security alert when risk or threat patterns are detected.
        """
        if risk_score <= 30 and not threat_type:
            return None

        # Determine default threat type and severity if not supplied
        if not threat_type:
            if 'UNAUTHORIZED_PATIENT' in action:
                threat_type = 'Unauthorized Patient Record Access'
            elif 'CONFIDENTIAL' in action:
                threat_type = 'Confidential Record Clearance Violation'
            elif 'INSIDER_THREAT' in action or 'BULK' in action:
                threat_type = 'Insider Threat: Anomalous Bulk Harvesting'
            elif 'LOGIN_FAILED' in action:
                threat_type = 'Brute Force Credential Attack'
            elif 'ADMIN' in action:
                threat_type = 'Privilege Escalation Attempt'
            else:
                threat_type = 'Suspicious Clinical Data Request'

        if not severity:
            if risk_score >= 81:
                severity = 'CRITICAL'
            elif risk_score >= 61:
                severity = 'HIGH'
            elif risk_score >= 31:
                severity = 'MEDIUM'
            else:
                severity = 'LOW'

        alert_id = f"ALT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        execute_db('''
            INSERT INTO security_alerts (alert_id, threat_type, severity, user_id, timestamp, risk_score, description, status)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, 'NEW')
        ''', (alert_id, threat_type, severity, user_id or 'UNKNOWN', risk_score, details))

        return alert_id

    @classmethod
    def check_insider_threat(cls, doctor_id, recent_views_count):
        """
        Detects anomalous behavior by authenticated doctors.
        If a doctor requests many patient records or unauthorized records in a short window:
        returns is_insider_threat=True
        """
        if recent_views_count >= 5:
            return True, "Clinician viewed > 5 distinct patient charts in rapid succession"
        return False, ""

    @classmethod
    def get_summary_stats(cls):
        """Returns statistics for dashboard metrics cards."""
        total_alerts = query_db("SELECT COUNT(*) as cnt FROM security_alerts", one=True)['cnt']
        critical_alerts = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE severity = 'CRITICAL'", one=True)['cnt']
        high_alerts = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE severity = 'HIGH'", one=True)['cnt']
        unresolved = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE status != 'RESOLVED'", one=True)['cnt']
        insider_threats = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE threat_type LIKE '%Insider Threat%'", one=True)['cnt']

        # Determine overall threat level
        if critical_alerts > 0 or unresolved >= 5:
            threat_level = 'CRITICAL'
            threat_color = 'threat-critical'
        elif high_alerts > 0 or unresolved >= 2:
            threat_level = 'HIGH'
            threat_color = 'threat-high'
        elif unresolved > 0:
            threat_level = 'ELEVATED'
            threat_color = 'threat-elevated'
        else:
            threat_level = 'LOW'
            threat_color = 'threat-low'

        return {
            'total_alerts': total_alerts,
            'critical_threats': critical_alerts,
            'high_threats': high_alerts,
            'unresolved_alerts': unresolved,
            'insider_threats': insider_threats,
            'threat_level': threat_level,
            'threat_color': threat_color
        }
