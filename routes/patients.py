from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.user import UserModel
from models.patient import PatientModel
from models.record import RecordModel
from services.risk_engine import RiskEngine
from services.audit_service import AuditService
from services.authorization_service import AuthorizationService
from services.threat_detector import ThreatDetector
from services.deception_service import DeceptionService

patients_bp = Blueprint('patients', __name__)

@patients_bp.route('/patients')
def patient_list():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = UserModel.get_by_user_id(session['user_id'])
    doc = UserModel.get_doctor_by_user_id(session['user_id'])
    doctor_id = doc['doctor_id'] if doc else None
    query_str = request.args.get('q', '').strip()

    if user['role'] == 'admin':
        patients = PatientModel.search(query_str) if query_str else PatientModel.get_all()
    else:
        # Doctor views assigned patients by default
        patients = PatientModel.search(query_str, doctor_id=doctor_id) if query_str else PatientModel.get_assigned_to_doctor(doctor_id)

    # Risk evaluation
    risk = RiskEngine.calculate_risk(
        user=user,
        action='VIEW_PATIENT_DIRECTORY',
        session_context={'device_id': session.get('device_id'), 'device_status': session.get('device_status'), 'ip_address': request.remote_addr or '127.0.0.1'}
    )

    AuditService.log(
        user_id=session['user_id'],
        role=user['role'],
        action='VIEW_PATIENT_LIST',
        ip_address=request.remote_addr or '127.0.0.1',
        device_status=session.get('device_status', 'TRUSTED'),
        risk_score=risk['score'],
        risk_level=risk['level'],
        result='SUCCESS',
        session_id=session.get('session_id'),
        details=f"Viewed heart patient catalog. Query: '{query_str}'"
    )

    return render_template('patient_list.html', patients=patients, user=user, doctor=doc, query_str=query_str, risk=risk)

@patients_bp.route('/patient/<patient_id>')
def patient_detail(patient_id):
    user = UserModel.get_by_user_id(session.get('user_id'))
    doc = UserModel.get_doctor_by_user_id(session.get('user_id')) if user else None
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()

    # If totally unauthenticated, direct to decoy honeypot immediately!
    if not user:
        risk = RiskEngine.calculate_risk(user=None, action='UNAUTHORIZED_ACCESS', patient={'patient_id': patient_id}, session_context={'ip_address': ip_address})
        ThreatDetector.analyze_event(
            user_id='ANONYMOUS_PROBE',
            action='UNAUTHORIZED_PATIENT_ACCESS',
            risk_score=risk['score'],
            details=f"Unauthenticated request targeting protected chart {patient_id}. Shunted to Decoy Sandbox.",
            threat_type='Unauthorized Patient Record Access',
            severity='CRITICAL'
        )
        DeceptionService.record_decoy_interaction(
            user_id='ANONYMOUS_PROBE',
            ip_address=ip_address,
            fake_patient_id=patient_id,
            action_performed='UNAUTHENTICATED_CHART_PROBE',
            risk_score=risk['score'],
            threat_level='CRITICAL'
        )
        AuditService.log(
            user_id='ANONYMOUS',
            role='unauthenticated',
            patient_id=patient_id,
            action='UNAUTHORIZED_PATIENT_ACCESS',
            ip_address=ip_address,
            risk_score=risk['score'],
            risk_level='CRITICAL',
            result='DECOY_SERVED',
            threat_type='UNAUTHORIZED_EXFILTRATION',
            details=f"Anonymous host probed {patient_id}. Real data shielded; Decoy served."
        )
        decoy_patient = DeceptionService.get_decoy_patient(patient_id)
        return render_template('patient_detail.html', patient=decoy_patient, is_decoy=True, risk=risk, is_emergency=False, access_status='RESTRICTED ACCESS (SECURITY MONITORING MODE)')

    # Check 1: Patient-Specific Authorization (Assigned or Emergency)
    is_authorized, auth_reason, is_emergency = AuthorizationService.can_access_patient(user, patient_id)

    # Fetch patient record to evaluate sensitivity
    real_patient = PatientModel.get_by_id(patient_id)

    # Check 2: Record Sensitivity Clearance
    sensitivity_allowed = True
    sensitivity_reason = ""
    if real_patient and user['role'] == 'doctor':
        sensitivity_allowed, sensitivity_reason = AuthorizationService.can_access_sensitivity(user, real_patient['record_sensitivity_level'])

    # Evaluate dynamic risk
    session_ctx = {
        'ip_address': ip_address,
        'device_id': session.get('device_id'),
        'device_status': session.get('device_status', 'UNKNOWN'),
        'session_id': session.get('session_id'),
        'is_emergency': is_emergency
    }
    risk = RiskEngine.calculate_risk(user=user, action='VIEW_PATIENT_RECORD', patient=real_patient or {'patient_id': patient_id}, session_context=session_ctx)

    # IF AUTHORIZATION FAILED OR SENSITIVITY FAILED OR RISK CRITICAL:
    if not is_authorized or not sensitivity_allowed or risk['score'] > 60:
        threat_type = "Unauthorized Cross-Patient Access" if not is_authorized else "Confidential Record Clearance Violation"
        if risk['score'] >= 80:
            threat_type = "Critical Unauthorized Exfiltration Attempt"

        ThreatDetector.analyze_event(
            user_id=session['user_id'],
            action='UNAUTHORIZED_PATIENT_ACCESS' if not is_authorized else 'CONFIDENTIAL_ACCESS_DENIED',
            risk_score=risk['score'],
            details=f"Clinician {user['name']} failed access check on {patient_id}: {auth_reason} {sensitivity_reason}",
            threat_type=threat_type,
            severity='CRITICAL' if risk['score'] >= 80 else 'HIGH'
        )

        DeceptionService.record_decoy_interaction(
            user_id=session['user_id'],
            ip_address=ip_address,
            fake_patient_id=patient_id,
            action_performed='RESTRICTED_ACCESS_INTERCEPTED',
            risk_score=risk['score'],
            threat_level=risk['level']
        )

        AuditService.log(
            user_id=session['user_id'],
            role=user['role'],
            patient_id=patient_id,
            action='UNAUTHORIZED_PATIENT_ACCESS' if not is_authorized else 'CONFIDENTIAL_ACCESS_DENIED',
            ip_address=ip_address,
            device_status=session.get('device_status', 'UNKNOWN'),
            risk_score=risk['score'],
            risk_level=risk['level'],
            result='DECOY_SERVED',
            threat_type=threat_type,
            session_id=session.get('session_id'),
            details=f"Access denied ({auth_reason or sensitivity_reason}). Shunted to Decoy Honeypot. Real data blocked."
        )

        decoy_patient = DeceptionService.get_decoy_patient(patient_id)
        flash(f"⚠️ Access Denied: {auth_reason or sensitivity_reason}. System active in Security Monitoring Mode.", "danger")
        return render_template(
            'patient_detail.html',
            patient=decoy_patient,
            is_decoy=True,
            risk=risk,
            user=user,
            doctor=doc,
            is_emergency=False,
            access_status='RESTRICTED ACCESS (SECURITY MONITORING MODE)'
        )

    # AUTHORIZED ACCESS GRANTED: Serve Real Protected Demo Record
    AuditService.log(
        user_id=session['user_id'],
        role=user['role'],
        patient_id=patient_id,
        action='VIEW_PATIENT_RECORD',
        ip_address=ip_address,
        device_status=session.get('device_status', 'TRUSTED'),
        risk_score=risk['score'],
        risk_level=risk['level'],
        result='SUCCESS',
        session_id=session.get('session_id'),
        details=f"Authorized clinician {user['name']} viewed chart {patient_id} ({'Emergency Break-Glass' if is_emergency else 'Assigned Care'})"
    )

    confidential_docs = RecordModel.get_confidential_records_by_patient(patient_id) if real_patient['record_sensitivity_level'] != 'NORMAL' else []

    return render_template(
        'patient_detail.html',
        patient=real_patient,
        is_decoy=False,
        risk=risk,
        user=user,
        doctor=doc,
        is_emergency=is_emergency,
        access_status='AUTHORIZED ACCESS',
        confidential_docs=confidential_docs
    )

@patients_bp.route('/patient/<patient_id>/update-notes', methods=['POST'])
def update_clinical_notes(patient_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        flash("Clinical authorization required.", "danger")
        return redirect(url_for('auth.login'))

    user = UserModel.get_by_user_id(session['user_id'])
    doc = UserModel.get_doctor_by_user_id(session['user_id'])
    doctor_id = doc['doctor_id'] if doc else None

    # Check assignment or emergency access
    is_authorized, reason, _ = AuthorizationService.can_access_patient(user, patient_id)
    if not is_authorized:
        flash("Cannot modify clinical records of unassigned patient.", "danger")
        return redirect(url_for('patients.patient_detail', patient_id=patient_id))

    notes = request.form.get('clinical_notes', '').strip()
    if notes:
        PatientModel.update_clinical_notes(patient_id, notes, doctor_id)
        AuditService.log(
            user_id=session['user_id'],
            role='doctor',
            patient_id=patient_id,
            action='UPDATE_CLINICAL_NOTES',
            ip_address=request.remote_addr or '127.0.0.1',
            device_status=session.get('device_status', 'TRUSTED'),
            risk_score=session.get('risk_score', 10),
            risk_level='LOW',
            result='SUCCESS',
            session_id=session.get('session_id'),
            details=f"Clinical progress note added by Dr. {user['name']} for patient {patient_id}"
        )
        flash("Clinical progress note recorded successfully.", "success")

    return redirect(url_for('patients.patient_detail', patient_id=patient_id))
