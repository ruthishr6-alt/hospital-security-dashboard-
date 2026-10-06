from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.db import query_db, execute_db
from services.auth_service import AuthService
from services.risk_engine import RiskEngine
from services.threat_detector import ThreatDetector
from services.deception_service import DeceptionService
from services.audit_service import AuditService
from models.patient import Patient

security_bp = Blueprint('security', __name__)

def current_admin():
    if 'user_id' not in session:
        return None
    user = AuthService.get_user_by_id(session['user_id'])
    if not user or user.get('role') != 'admin':
        return None
    return user

@security_bp.before_request
def check_security_access():
    if request.endpoint and 'static' not in request.endpoint:
        # Simulator page can be viewed or used by admin, but let's allow doctors read-only or restrict to admin
        if 'user_id' not in session:
            flash("Administrator security access required.", "warning")
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash("⛔ Unauthorized: Security telemetries are restricted to Security Administrators.", "danger")
            return redirect(url_for('doctor.dashboard'))

@security_bp.route('/security/alerts')
def alerts():
    admin = current_admin()
    severity_filter = request.args.get('severity')
    
    if severity_filter:
        events = query_db("SELECT * FROM security_events WHERE severity = ? ORDER BY timestamp DESC", (severity_filter,))
    else:
        events = query_db("SELECT * FROM security_events ORDER BY timestamp DESC")

    threat_stats = ThreatDetector.get_threat_summary()

    return render_template(
        'security_alerts.html',
        user=admin,
        events=events,
        stats=threat_stats,
        severity_filter=severity_filter
    )

@security_bp.route('/security/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    admin = current_admin()
    execute_db("UPDATE security_events SET resolved = 1 WHERE id = ?", (alert_id,))
    AuditService.log(
        action='RESOLVE_SECURITY_ALERT',
        risk_result={'score': 5, 'level': 'LOW', 'response_mode': 'REAL_SERVED'},
        user=admin,
        request_obj=request,
        resource='ALERT_DISPOSITION',
        details=f"Admin {admin['name']} marked alert #{alert_id} as resolved"
    )
    flash(f"Security Alert #{alert_id} resolved.", "success")
    return redirect(url_for('security.alerts'))

@security_bp.route('/security/threats')
def threat_monitor():
    admin = current_admin()
    threats = query_db("SELECT * FROM security_events ORDER BY timestamp DESC LIMIT 100")
    threat_stats = ThreatDetector.get_threat_summary()

    # Top targeted IPs and resources
    top_attackers = query_db('''
        SELECT ip_address, COUNT(*) as hit_count, MAX(risk_score) as peak_risk
        FROM security_events
        GROUP BY ip_address
        ORDER BY hit_count DESC
        LIMIT 5
    ''')

    return render_template(
        'threat_monitor.html',
        user=admin,
        threats=threats,
        stats=threat_stats,
        top_attackers=top_attackers
    )

@security_bp.route('/security/honeypot')
def honeypot_monitor():
    admin = current_admin()
    sessions = DeceptionService.get_decoy_sessions(limit=100)
    stats = DeceptionService.get_decoy_stats()
    decoys = query_db("SELECT * FROM decoy_patients ORDER BY patient_id")

    return render_template(
        'honeypot_monitor.html',
        user=admin,
        sessions=sessions,
        stats=stats,
        decoys=decoys
    )

@security_bp.route('/security/audit-logs')
def audit_logs():
    admin = current_admin()
    status_filter = request.args.get('status')
    risk_filter = request.args.get('risk')
    search_term = request.args.get('q', '').strip()

    logs = AuditService.get_logs(
        limit=100,
        status_filter=status_filter,
        risk_filter=risk_filter,
        search_term=search_term
    )
    summary = AuditService.get_audit_summary()

    return render_template(
        'audit_logs.html',
        user=admin,
        logs=logs,
        summary=summary,
        status_filter=status_filter,
        risk_filter=risk_filter,
        search_term=search_term
    )

@security_bp.route('/security/risk-analysis')
def risk_analysis():
    admin = current_admin()
    # Sample evaluation to display live factor weights
    sample_eval = RiskEngine.evaluate_request(
        user=admin,
        target_patient_id='HP-501',
        request_obj=request,
        resource_name='RISK_ANALYZER_VIEW'
    )
    return render_template('risk_analysis.html', user=admin, sample_eval=sample_eval)

@security_bp.route('/security/simulator')
def simulator():
    admin = current_admin()
    return render_template('simulator.html', user=admin)

@security_bp.route('/api/security/simulate-attack', methods=['POST'])
def simulate_attack():
    """
    Simulates attacks for live demo:
    - FLOW 1: Doctor legitimate access
    - FLOW 2: Brute force attack by unknown user
    - FLOW 3: Rapid record bulk scraping / enumeration
    - FLOW 4: Unauthorized cross-patient access attempt
    - FLOW 5: SQL Injection probe
    - FLOW 6: Direct Honeypot tripwire touch
    """
    data = request.get_json() or {}
    attack_type = data.get('scenario', 'flow2')

    ip_fake = data.get('ip', '203.0.113.195')
    simulated_request = type('RequestShim', (), {
        'remote_addr': ip_fake,
        'headers': {'User-Agent': data.get('user_agent', 'Mozilla/5.0 KaliLinux-Attacker')},
        'path': '/api/patients/bulk',
        'query_string': b'query=SELECT * FROM real_patients',
        'is_json': False
    })()

    if attack_type == 'flow1':
        # FLOW 1: Legitimate Doctor access from authorized hospital workstation
        doc = AuthService.get_user_by_id('DOC101')
        doc_request = type('RequestShim', (), {
            'remote_addr': '192.168.1.101',
            'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) Hospital-Workstation-ICU'},
            'path': '/patient/HP-501',
            'query_string': b'',
            'is_json': False
        })()
        risk = RiskEngine.evaluate_request(user=doc, target_patient_id='HP-501', request_obj=doc_request)
        AuditService.log('VIEW_PATIENT_RECORD', risk, doc, doc_request, 'HP-501', 'CLINICAL_CHART', 'Dr. Roberts legitimately accessed assigned HP-501 chart')
        patient = Patient.get_by_id_real('HP-501')
        return jsonify({
            'success': True,
            'scenario': 'Flow 1: Legitimate Cardiologist Access',
            'risk': risk,
            'status': 'ALLOWED',
            'response_mode': 'REAL_DATA_SERVED',
            'patient_served': {'id': patient['patient_id'], 'name': patient['name'], 'is_decoy': 0},
            'message': 'Doctor authenticated + assigned patient → LOW RISK (15) → Real patient data served.'
        })

    elif attack_type == 'flow2':
        # FLOW 2: Brute force login by unknown user
        # Record repeated failures
        for _ in range(4):
            AuthService.record_failed_attempt(ip_fake, 'admin')
        risk = RiskEngine.evaluate_request(user=None, request_obj=simulated_request, resource_name='LOGIN_PORTAL')
        threat = ThreatDetector.process_threat(None, simulated_request, risk, action_name='BRUTE_FORCE_ATTACK')
        DeceptionService.log_interaction(simulated_request, None, 'HP-DECOY-1042', 'BRUTE_FORCE_EXPLOIT', 'Attacker credential stuffing trapped.')
        AuditService.log('BRUTE_FORCE_LOGIN_ATTACK', risk, None, simulated_request, None, 'AUTH_PORTAL', 'Multiple failed login attempts detected. Shunted to Decoy sandbox.')
        decoy_patient = DeceptionService.get_decoy_patient('HP-DECOY-1042')

        return jsonify({
            'success': True,
            'scenario': 'Flow 2: Unknown User Brute-Force Attack',
            'risk': risk,
            'status': 'BLOCKED',
            'response_mode': 'DECOY_ACTIVATED',
            'threat_alert': threat,
            'patient_served': {'id': decoy_patient['patient_id'], 'name': decoy_patient['name'], 'is_decoy': 1},
            'message': 'Unknown user + repeated failed attempts → CRITICAL RISK (92) → Real medical records blocked → Decoy environment activated.'
        })

    elif attack_type == 'flow3':
        # FLOW 3: Rapid bulk patient scraping
        # Trigger velocity window
        from services.risk_engine import _request_history
        import time
        now = time.time()
        _request_history[ip_fake] = [now - i for i in range(12)] # 12 requests in 10s
        risk = RiskEngine.evaluate_request(user=None, request_obj=simulated_request, requested_count=25)
        threat = ThreatDetector.process_threat(None, simulated_request, risk, action_name='RAPID_BULK_SCRAPING')
        DeceptionService.log_interaction(simulated_request, None, 'HP-DECOY-1111', 'BULK_SCRAPE_EXFILTRATION', 'Attacker scraped 25 records. Fed decoy honeytokens.')
        AuditService.log('RAPID_ENUMERATION_ATTACK', risk, None, simulated_request, None, 'PATIENT_API', 'Scraper detected (12 req/10s). Real DB blocked; decoy records served.')
        decoy_list = DeceptionService.get_decoy_patient_list()

        return jsonify({
            'success': True,
            'scenario': 'Flow 3: Rapid Record Bulk Scraping Attack',
            'risk': risk,
            'status': 'BLOCKED',
            'response_mode': 'DECOY_ACTIVATED',
            'threat_alert': threat,
            'records_served_count': len(decoy_list),
            'decoy_sample': decoy_list[0]['patient_id'],
            'message': 'Rapid scraping pattern detected → CRITICAL RISK (94) → Real patient DB shielded → Decoy honeypot records streamed to attacker.'
        })

    elif attack_type == 'cross_patient':
        # Cross-patient access violation: Dr Chang DOC102 tries to view HP-501 (Dr Roberts)
        doc = AuthService.get_user_by_id('DOC102')
        risk = RiskEngine.evaluate_request(user=doc, target_patient_id='HP-501', request_obj=simulated_request)
        threat = ThreatDetector.process_threat(doc, simulated_request, risk, 'HP-501', 'CROSS_PATIENT_ACCESS')
        decoy_patient = DeceptionService.get_decoy_patient('HP-501')
        AuditService.log('CROSS_PATIENT_ACCESS_ATTEMPT', risk, doc, simulated_request, 'HP-501', 'PATIENT_CHART', 'Dr. Chang attempted access to unassigned patient HP-501')
        return jsonify({
            'success': True,
            'scenario': 'Cross-Patient Privilege Violation',
            'risk': risk,
            'status': 'BLOCKED',
            'response_mode': 'DECOY_ACTIVATED',
            'threat_alert': threat,
            'patient_served': {'id': decoy_patient['patient_id'], 'name': decoy_patient['name'], 'is_decoy': 1},
            'message': 'Authenticated Doctor targeting unassigned patient → HIGH RISK (75) → Access to real record blocked → Decoy served.'
        })

    elif attack_type == 'sqli':
        # SQL Injection Probe
        sqli_request = type('RequestShim', (), {
            'remote_addr': ip_fake,
            'headers': {'User-Agent': 'sqlmap/1.8#dev'},
            'path': '/api/patient',
            'query_string': b"search=' OR '1'='1' --",
            'is_json': False
        })()
        risk = RiskEngine.evaluate_request(user=None, request_obj=sqli_request)
        threat = ThreatDetector.process_threat(None, sqli_request, risk, action_name='SQLI_EXPLOIT')
        DeceptionService.log_interaction(sqli_request, None, 'HP-DECOY-1100', 'SQL_INJECTION_PROBE', 'Attacker tested OR 1=1 tokens.')
        AuditService.log('SQL_INJECTION_PROBE', risk, None, sqli_request, None, 'QUERY_API', 'SQLi tokens intercepted. Decoy canary table returned.')
        return jsonify({
            'success': True,
            'scenario': 'SQL Injection / Exploit Payload Attack',
            'risk': risk,
            'status': 'BLOCKED',
            'response_mode': 'DECOY_ACTIVATED',
            'threat_alert': threat,
            'message': 'SQL injection signatures detected in payload → CRITICAL RISK (96) → Payload defused → Decoy table served.'
        })

    return jsonify({'error': 'Unknown scenario'}), 400

@security_bp.route('/api/security/chart-data')
def chart_data():
    """Returns aggregated data for Chart.js dashboard charts."""
    # 1. Login Attempts (Success vs Failed)
    successful_logins = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE action = 'AUTHENTICATE_LOGIN'", one=True)['cnt']
    failed_logins = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE action = 'FAILED_LOGIN_ATTEMPT' OR action = 'BRUTE_FORCE_LOGIN_ATTACK'", one=True)['cnt']

    # 2. Allowed vs Blocked vs Flagged
    allowed_count = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE status = 'ALLOWED'", one=True)['cnt']
    blocked_count = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE status = 'BLOCKED'", one=True)['cnt']
    flagged_count = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE status = 'FLAGGED'", one=True)['cnt']

    # 3. Threats by Severity
    critical_threats = query_db("SELECT COUNT(*) as cnt FROM security_events WHERE severity = 'CRITICAL'", one=True)['cnt']
    high_threats = query_db("SELECT COUNT(*) as cnt FROM security_events WHERE severity = 'HIGH'", one=True)['cnt']
    medium_threats = query_db("SELECT COUNT(*) as cnt FROM security_events WHERE severity = 'MEDIUM'", one=True)['cnt']

    # 4. Decoy Interactions by Canary Patient
    decoy_by_patient = query_db('''
        SELECT decoy_patient_id, COUNT(*) as hits
        FROM decoy_interactions
        GROUP BY decoy_patient_id
        ORDER BY hits DESC
        LIMIT 6
    ''')

    # 5. Security Events Timeline (last 7 entries)
    events_timeline = query_db('''
        SELECT timestamp, threat_type, risk_score
        FROM security_events
        ORDER BY timestamp ASC
        LIMIT 10
    ''')

    return jsonify({
        'logins': {
            'labels': ['Authorized Logins', 'Failed / Blocked Attempts'],
            'data': [successful_logins, failed_logins]
        },
        'access_status': {
            'labels': ['Allowed (Low Risk)', 'Blocked (Decoy Triggered)', 'Flagged (Elevated Monitoring)'],
            'data': [allowed_count, blocked_count, flagged_count]
        },
        'threats_severity': {
            'labels': ['Critical Severity (Risk > 80)', 'High Severity (Risk 61-80)', 'Medium Severity (Risk 31-60)'],
            'data': [critical_threats, high_threats, medium_threats]
        },
        'decoy_canaries': {
            'labels': [d['decoy_patient_id'] for d in decoy_by_patient] or ['HP-DECOY-1042', 'HP-DECOY-1088', 'HP-DECOY-1111'],
            'data': [d['hits'] for d in decoy_by_patient] or [5, 3, 2]
        },
        'timeline': {
            'labels': [e['timestamp'].split(' ')[-1] if ' ' in e['timestamp'] else e['timestamp'] for e in events_timeline],
            'scores': [e['risk_score'] for e in events_timeline]
        }
    })
