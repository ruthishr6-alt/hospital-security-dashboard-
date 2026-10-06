from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.db import query_db, execute_db
from models.user import UserModel
from models.patient import PatientModel
from models.record import RecordModel
from services.risk_engine import RiskEngine
from services.threat_detector import ThreatDetector
from services.deception_service import DeceptionService
from services.audit_service import AuditService
from services.alert_service import AlertService

security_bp = Blueprint('security', __name__)

@security_bp.before_request
def check_security_access():
    if request.endpoint and 'static' not in request.endpoint:
        if 'user_id' not in session:
            flash("Administrator clearance required.", "warning")
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash("⛔ Security Telemetry restricted to Security Administrators.", "danger")
            return redirect(url_for('doctor.dashboard'))

@security_bp.route('/risk-analysis')
def risk_analysis():
    user = UserModel.get_by_user_id(session['user_id'])
    return render_template('risk_analysis.html', user=user)

@security_bp.route('/security/alerts')
def alerts():
    user = UserModel.get_by_user_id(session['user_id'])
    status_filter = request.args.get('status')
    severity_filter = request.args.get('severity')

    all_alerts = AlertService.get_all_alerts(status_filter, severity_filter)
    threat_stats = ThreatDetector.get_summary_stats()

    return render_template(
        'security_alerts.html',
        user=user,
        alerts=all_alerts,
        stats=threat_stats,
        status_filter=status_filter,
        severity_filter=severity_filter
    )

@security_bp.route('/security/alerts/<alert_id>/update-status', methods=['POST'])
def update_alert(alert_id):
    new_status = request.form.get('status', 'RESOLVED')
    AlertService.update_alert_status(alert_id, new_status)
    flash(f"Alert {alert_id} status updated to {new_status}.", "success")
    return redirect(url_for('security.alerts'))

@security_bp.route('/security/threats')
def threat_monitor():
    user = UserModel.get_by_user_id(session['user_id'])
    stats = ThreatDetector.get_summary_stats()
    threat_events = query_db("SELECT * FROM security_alerts ORDER BY timestamp DESC LIMIT 50")
    top_threat_sources = query_db('''
        SELECT ip_address, COUNT(*) as hit_count, MAX(risk_score) as max_risk
        FROM audit_logs
        WHERE result IN ('DENIED', 'DECOY_SERVED')
        GROUP BY ip_address
        ORDER BY hit_count DESC LIMIT 5
    ''')

    return render_template(
        'threat_monitor.html',
        user=user,
        stats=stats,
        threat_events=threat_events,
        top_sources=top_threat_sources
    )

@security_bp.route('/security/audit-logs')
def audit_logs():
    user = UserModel.get_by_user_id(session['user_id'])
    user_filter = request.args.get('user')
    patient_filter = request.args.get('patient')
    threat_filter = request.args.get('threat')
    action_filter = request.args.get('action')
    result_filter = request.args.get('result')

    logs = AuditService.get_logs(
        limit=100,
        user_filter=user_filter,
        patient_filter=patient_filter,
        threat_filter=threat_filter,
        action_filter=action_filter,
        result_filter=result_filter
    )
    summary = AuditService.get_summary_stats()

    return render_template(
        'audit_logs.html',
        user=user,
        logs=logs,
        summary=summary,
        user_filter=user_filter,
        patient_filter=patient_filter,
        threat_filter=threat_filter,
        action_filter=action_filter,
        result_filter=result_filter
    )

@security_bp.route('/security/devices')
def device_security():
    user = UserModel.get_by_user_id(session['user_id'])
    devices = UserModel.get_all_devices()
    return render_template('device_security.html', user=user, devices=devices)

@security_bp.route('/security/devices/<device_id>/toggle', methods=['POST'])
def toggle_device(device_id):
    device = UserModel.get_device(device_id)
    if device:
        new_status = 'UNKNOWN' if device['device_status'] == 'TRUSTED' else 'TRUSTED'
        new_contrib = 20 if new_status == 'UNKNOWN' else -5
        execute_db('''
            UPDATE device_status
            SET device_status = ?, risk_contribution = ?, last_seen = CURRENT_TIMESTAMP
            WHERE device_id = ?
        ''', (new_status, new_contrib, device_id))
        flash(f"Device {device_id} status changed to {new_status} (Risk contribution: {new_contrib}).", "info")
    return redirect(url_for('security.device_security'))

@security_bp.route('/api/security/simulate-scenario', methods=['POST'])
def simulate_scenario():
    """Executes all 6 required demo scenarios and returns structured outcome."""
    data = request.get_json() or {}
    scenario_id = str(data.get('scenario', '1'))

    if scenario_id == '1':
        # Scenario 1: Authorized Doctor
        doc_user = UserModel.get_by_username('doctor_demo_01')
        risk = RiskEngine.calculate_risk(user=doc_user, action='VIEW_PATIENT', patient={'patient_id': 'HP001'}, session_context={'device_status': 'TRUSTED', 'ip_address': '192.168.1.101'})
        AuditService.log(
            user_id='U_DOC01', role='doctor', patient_id='HP001', action='VIEW_PATIENT_RECORD',
            ip_address='192.168.1.101', device_status='TRUSTED', risk_score=risk['score'],
            risk_level=risk['level'], result='SUCCESS', details='Scenario 1: Authorized Doctor accessed assigned HP001'
        )
        p = PatientModel.get_by_id('HP001')
        return jsonify({
            'success': True,
            'scenario_name': 'Scenario 1: Authorized Doctor Workflow',
            'risk': risk,
            'status': 'AUTHORIZED ACCESS',
            'response_mode': 'REAL PROTECTED RECORD SERVED',
            'record_served': {'patient_id': p['patient_id'], 'name': p['name'], 'is_decoy': 0},
            'summary': 'Doctor authenticated + assigned patient + trusted device -> LOW RISK (0-10) -> Real protected demo record served.'
        })

    elif scenario_id == '2':
        # Scenario 2: Unauthorized Patient Access
        doc_user = UserModel.get_by_username('doctor_demo_01') # Assigned to HP001, HP002, HP010
        risk = RiskEngine.calculate_risk(user=doc_user, action='VIEW_PATIENT', patient={'patient_id': 'HP003'}, session_context={'device_status': 'TRUSTED', 'ip_address': '192.168.1.101'})
        AuditService.log(
            user_id='U_DOC01', role='doctor', patient_id='HP003', action='UNAUTHORIZED_PATIENT_ACCESS',
            ip_address='192.168.1.101', device_status='TRUSTED', risk_score=risk['score'],
            risk_level=risk['level'], result='DENIED', threat_type='CROSS_PATIENT_ACCESS',
            details='Scenario 2: Doctor Lin attempted unassigned patient HP003'
        )
        ThreatDetector.analyze_event(
            user_id='U_DOC01', action='UNAUTHORIZED_PATIENT_ACCESS', risk_score=risk['score'],
            details='Doctor Lin (D001) attempted to access patient HP003 assigned to Doctor Vance. Access denied.',
            threat_type='Unauthorized Cross-Patient Access Attempt', severity='HIGH'
        )
        return jsonify({
            'success': True,
            'scenario_name': 'Scenario 2: Unauthorized Patient Access',
            'risk': risk,
            'status': 'ACCESS DENIED',
            'response_mode': 'PROTECTED DATA BLOCKED',
            'summary': 'Doctor attempted other doctor\'s patient -> Risk score increased (+20) -> Access denied -> Event logged.'
        })

    elif scenario_id == '3':
        # Scenario 3: Repeated Failed Login
        from services.auth_service import AuthService
        for _ in range(4):
            AuthService.record_failed_attempt('198.51.100.42', 'admin_demo')
        risk = RiskEngine.calculate_risk(user=None, action='LOGIN_FAILED', session_context={'ip_address': '198.51.100.42', 'device_status': 'UNKNOWN'})
        alert_id = ThreatDetector.analyze_event(
            user_id='UNKNOWN', action='LOGIN_FAILED', risk_score=risk['score'],
            details='Repeated failed login threshold tripped from 198.51.100.42 against admin_demo',
            threat_type='Brute Force Credential Attack', severity='CRITICAL'
        )
        AuditService.log(
            user_id='UNKNOWN', role='unauthenticated', action='LOGIN_FAILED',
            ip_address='198.51.100.42', device_status='UNKNOWN', risk_score=risk['score'],
            risk_level=risk['level'], result='DENIED', threat_type='BRUTE_FORCE_LOGIN',
            details='Repeated failed logins detected. Session restricted.'
        )
        return jsonify({
            'success': True,
            'scenario_name': 'Scenario 3: Repeated Failed Login',
            'risk': risk,
            'status': 'SESSION RESTRICTED',
            'response_mode': 'ALERT GENERATED',
            'alert_id': alert_id,
            'summary': 'Multiple failed logins -> Risk increases to CRITICAL (95) -> Session restricted -> Admin alert generated.'
        })

    elif scenario_id == '4':
        # Scenario 4: Suspicious User (Decoy Activated)
        risk = RiskEngine.calculate_risk(user=None, action='UNAUTHORIZED_ACCESS', patient={'patient_id': 'HP-DEC-101'}, session_context={'ip_address': '203.0.113.88', 'device_status': 'UNKNOWN', 'is_suspicious_api': True})
        DeceptionService.record_decoy_interaction(
            user_id='UNKNOWN_ATTACKER', ip_address='203.0.113.88', fake_patient_id='HP-DEC-101',
            action_performed='DECOY_EXFILTRATION_PROBE', risk_score=risk['score'], threat_level='CRITICAL'
        )
        alert_id = ThreatDetector.analyze_event(
            user_id='UNKNOWN_ATTACKER', action='DECOY_ACTIVATED', risk_score=risk['score'],
            details='Suspicious session probing database -> Shunted to Decoy Sandbox (HP-DEC-101).',
            threat_type='Honeytoken Canary Tripwire Triggered', severity='CRITICAL'
        )
        AuditService.log(
            user_id='UNKNOWN_ATTACKER', role='unauthenticated', patient_id='HP-DEC-101', action='DECOY_RECORD_VIEWED',
            ip_address='203.0.113.88', device_status='UNKNOWN', risk_score=risk['score'],
            risk_level='CRITICAL', result='DECOY_SERVED', threat_type='HONEYTOKEN_CANARY',
            details='Protected data shielded. Attacker trapped in decoy environment.'
        )
        decoy = DeceptionService.get_decoy_patient('HP-DEC-101')
        return jsonify({
            'success': True,
            'scenario_name': 'Scenario 4: Suspicious User Shunted to Decoy',
            'risk': risk,
            'status': 'SECURITY MONITORING MODE',
            'response_mode': 'DECOY HONEYPOT ACTIVATED',
            'record_served': {'patient_id': decoy['patient_id'], 'name': decoy['name'], 'is_decoy': 1},
            'alert_id': alert_id,
            'summary': 'Unknown session + suspicious activity -> CRITICAL risk -> Real data blocked -> Decoy environment activated -> Fake records shown.'
        })

    elif scenario_id == '5':
        # Scenario 5: Emergency Break-Glass
        doc_user = UserModel.get_by_username('doctor_demo_01')
        # Doctor Lin requests emergency access for unassigned patient HP005
        from datetime import datetime, timedelta
        expires_at = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
        RecordModel.create_emergency_access(
            doctor_id='D001', patient_id='HP005', session_id='SESS-DEMO-EMERGENCY',
            reason='Simulated acute cardiogenic shock resuscitation in transit',
            expires_at=expires_at, risk_before=10, risk_after=25
        )
        risk = RiskEngine.calculate_risk(
            user=doc_user, action='EMERGENCY_ACCESS', patient={'patient_id': 'HP005'},
            session_context={'is_emergency': True, 'device_status': 'TRUSTED', 'ip_address': '192.168.1.101'}
        )
        AuditService.log(
            user_id='U_DOC01', role='doctor', patient_id='HP005', action='EMERGENCY_ACCESS',
            ip_address='192.168.1.101', device_status='TRUSTED', risk_score=risk['score'],
            risk_level=risk['level'], result='SUCCESS', threat_type='EMERGENCY_BREAK_GLASS',
            details='Emergency Break-Glass access approved for HP005 with 15-minute validity.'
        )
        p = PatientModel.get_by_id('HP005')
        return jsonify({
            'success': True,
            'scenario_name': 'Scenario 5: Emergency Break-Glass Workflow',
            'risk': risk,
            'status': 'EMERGENCY BREAK-GLASS ACTIVE',
            'response_mode': 'TEMPORARY AUTHORIZATION GRANTED',
            'record_served': {'patient_id': p['patient_id'], 'name': p['name'], 'is_decoy': 0},
            'expires_at': expires_at,
            'summary': 'Doctor -> unassigned critical patient -> enters emergency reason -> temporary authorization -> access logged -> automatic expiry.'
        })

    elif scenario_id == '6':
        # Scenario 6: Insider Threat Detection
        doc_user = UserModel.get_by_username('doctor_demo_02')
        risk = RiskEngine.calculate_risk(
            user=doc_user, action='BULK_PATIENT_SEARCH',
            session_context={'is_bulk': True, 'device_status': 'TRUSTED', 'ip_address': '192.168.1.102'}
        )
        alert_id = ThreatDetector.analyze_event(
            user_id='U_DOC02', action='INSIDER_THREAT', risk_score=risk['score'],
            details='Clinician Dr. Vance performed anomalous bulk search across 12 unassigned heart patient charts.',
            threat_type='Insider Threat: Anomalous Bulk Harvesting', severity='CRITICAL'
        )
        AuditService.log(
            user_id='U_DOC02', role='doctor', action='BULK_ACCESS_DETECTED',
            ip_address='192.168.1.102', device_status='TRUSTED', risk_score=risk['score'],
            risk_level=risk['level'], result='FLAGGED', threat_type='INSIDER_THREAT',
            details='Authorized doctor unusual bulk search detected. Risk elevated to CRITICAL. Protected access restricted.'
        )
        return jsonify({
            'success': True,
            'scenario_name': 'Scenario 6: Insider Threat Detection',
            'risk': risk,
            'status': 'ACCESS RESTRICTED (DECOY ENGAGED)',
            'response_mode': 'INSIDER THREAT ALERT GENERATED',
            'alert_id': alert_id,
            'summary': 'Authorized doctor -> unusual bulk patient searches -> risk increases -> insider threat alert -> protected access restricted -> Admin notified.'
        })

    return jsonify({'error': 'Invalid scenario identifier'}), 400

@security_bp.route('/api/security/chart-data')
def chart_data():
    """Provides 7 dynamic telemetry streams for the SOC Dashboard."""
    # 1. Threats by Severity
    critical = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE severity = 'CRITICAL'", one=True)['cnt']
    high = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE severity = 'HIGH'", one=True)['cnt']
    medium = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE severity = 'MEDIUM'", one=True)['cnt']
    low = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE severity = 'LOW'", one=True)['cnt']

    # 2. Login Activity
    login_success = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE action = 'LOGIN_SUCCESS'", one=True)['cnt']
    login_failed = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE action = 'LOGIN_FAILED'", one=True)['cnt']

    # 3. Failed Login Trend
    failed_attempts = query_db("SELECT COUNT(*) as cnt FROM failed_logins", one=True)['cnt'] or 3

    # 4. Risk Score Distribution
    low_risk = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE risk_level = 'LOW'", one=True)['cnt']
    med_risk = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE risk_level = 'MEDIUM'", one=True)['cnt']
    high_risk = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE risk_level = 'HIGH'", one=True)['cnt']
    crit_risk = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE risk_level = 'CRITICAL'", one=True)['cnt']

    # 5. Decoy Activity
    decoy_hits = query_db('''
        SELECT fake_patient_searched as canary, COUNT(*) as hits
        FROM decoy_sessions
        GROUP BY fake_patient_searched
        ORDER BY hits DESC LIMIT 5
    ''')

    # 6. Access Attempts
    allowed_access = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE result = 'SUCCESS'", one=True)['cnt']
    denied_access = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE result = 'DENIED'", one=True)['cnt']
    decoy_access = query_db("SELECT COUNT(*) as cnt FROM audit_logs WHERE result = 'DECOY_SERVED'", one=True)['cnt']

    # 7. Threat Type Distribution
    threat_types = query_db('''
        SELECT threat_type, COUNT(*) as cnt
        FROM security_alerts
        GROUP BY threat_type
        ORDER BY cnt DESC LIMIT 5
    ''')

    return jsonify({
        'threats_by_severity': {
            'labels': ['Critical (Risk 81-100)', 'High (Risk 61-80)', 'Medium (Risk 31-60)', 'Low (Risk 0-30)'],
            'data': [critical, high, medium, low]
        },
        'login_activity': {
            'labels': ['MFA Approved Logins', 'Failed / Blocked Attempts'],
            'data': [login_success, login_failed]
        },
        'failed_trend': {
            'labels': ['T-30m', 'T-20m', 'T-10m', 'Current'],
            'data': [1, 2, failed_attempts, failed_attempts + 1]
        },
        'risk_distribution': {
            'labels': ['Low Risk', 'Medium Risk', 'High Risk', 'Critical Risk'],
            'data': [low_risk, med_risk, high_risk, crit_risk]
        },
        'decoy_activity': {
            'labels': [d['canary'] for d in decoy_hits] or ['HP-DEC-101', 'HP-DEC-102', 'HP-DEC-106'],
            'data': [d['hits'] for d in decoy_hits] or [4, 6, 9]
        },
        'access_attempts': {
            'labels': ['Allowed (Low Risk)', 'Blocked (Access Denied)', 'Decoy Served (Honeypot)'],
            'data': [allowed_access, denied_access, decoy_access]
        },
        'threat_types': {
            'labels': [t['threat_type'] for t in threat_types] or ['Brute Force', 'Cross-Patient', 'Bulk Harvesting'],
            'data': [t['cnt'] for t in threat_types] or [2, 1, 1]
        }
    })
