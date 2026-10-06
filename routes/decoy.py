from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from services.deception_service import DeceptionService
from services.audit_service import AuditService
from models.user import UserModel

decoy_bp = Blueprint('decoy', __name__)

@decoy_bp.route('/decoy')
def decoy_catalog():
    """
    Renders isolated Decoy Honeypot Environment.
    Displays synthetic decoy patients under 'SECURITY MONITORING MODE'.
    """
    decoy_patients = DeceptionService.get_all_decoy_patients()
    user = UserModel.get_by_user_id(session.get('user_id'))
    
    # Record query into decoy_sessions
    DeceptionService.record_decoy_interaction(
        user_id=session.get('user_id', 'SUSPICIOUS_CLIENT'),
        ip_address=request.remote_addr or '127.0.0.1',
        fake_patient_id='CATALOG_BROWSE',
        action_performed='DECOY_CATALOG_EXPLORATION',
        risk_score=session.get('risk_score', 85),
        threat_level=session.get('risk_level', 'CRITICAL')
    )

    return render_template('decoy.html', patients=decoy_patients, user=user)

@decoy_bp.route('/decoy/<patient_id>')
def decoy_detail(patient_id):
    patient = DeceptionService.get_decoy_patient(patient_id)
    user = UserModel.get_by_user_id(session.get('user_id'))

    DeceptionService.record_decoy_interaction(
        user_id=session.get('user_id', 'SUSPICIOUS_CLIENT'),
        ip_address=request.remote_addr or '127.0.0.1',
        fake_patient_id=patient_id,
        action_performed='DECOY_RECORD_EXFILTRATE',
        risk_score=session.get('risk_score', 90),
        threat_level='CRITICAL'
    )

    AuditService.log(
        user_id=session.get('user_id', 'UNKNOWN'),
        role=session.get('role', 'unauthenticated'),
        patient_id=patient_id,
        action='DECOY_RECORD_VIEWED',
        ip_address=request.remote_addr or '127.0.0.1',
        device_status=session.get('device_status', 'UNKNOWN'),
        risk_score=session.get('risk_score', 90),
        risk_level='CRITICAL',
        result='DECOY_SERVED',
        threat_type='HONEYPOT_EXFILTRATION',
        details=f"Attacker inspected synthetic honeypot record {patient_id} in isolated sandbox"
    )

    return render_template(
        'patient_detail.html',
        patient=patient,
        is_decoy=True,
        risk={'score': 90, 'level': 'CRITICAL', 'reasons': [{'factor': 'Decoy Sandbox Enforced', 'delta': +90, 'type': 'HONEYPOT', 'description': 'Session confined to isolated synthetic sandbox.'}]},
        user=user,
        access_status='RESTRICTED ACCESS (SECURITY MONITORING MODE)'
    )

@decoy_bp.route('/security/decoy-monitor')
def decoy_monitor():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Administrator clearance required.", "warning")
        return redirect(url_for('auth.login'))

    user = UserModel.get_by_user_id(session['user_id'])
    sessions = DeceptionService.get_decoy_sessions(limit=50)
    stats = DeceptionService.get_stats()
    canaries = DeceptionService.get_all_decoy_patients()

    return render_template(
        'decoy_monitor.html',
        user=user,
        sessions=sessions,
        stats=stats,
        canaries=canaries
    )
