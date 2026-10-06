from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.user import UserModel
from models.patient import PatientModel
from models.record import RecordModel
from services.risk_engine import RiskEngine
from services.audit_service import AuditService
from services.authorization_service import AuthorizationService
from services.threat_detector import ThreatDetector
from services.deception_service import DeceptionService

doctor_bp = Blueprint('doctor', __name__)

@doctor_bp.before_request
def verify_doctor_auth():
    if request.endpoint and 'static' not in request.endpoint:
        if 'user_id' not in session:
            flash("Clinical authentication required.", "warning")
            return redirect(url_for('auth.login'))
        if session.get('role') != 'doctor':
            flash("Clinical credentials required.", "warning")
            return redirect(url_for('admin.dashboard'))

@doctor_bp.route('/doctor/dashboard')
def dashboard():
    user = UserModel.get_by_user_id(session['user_id'])
    doc = UserModel.get_doctor_by_user_id(session['user_id'])
    doctor_id = doc['doctor_id'] if doc else 'D001'

    # Compute risk score
    risk = RiskEngine.calculate_risk(
        user=user,
        action='VIEW_DOCTOR_DASHBOARD',
        session_context={
            'device_id': session.get('device_id'),
            'device_status': session.get('device_status'),
            'ip_address': request.remote_addr or '127.0.0.1',
            'session_id': session.get('session_id')
        }
    )
    session['risk_score'] = risk['score']
    session['risk_level'] = risk['level']

    # Get Assigned Patients
    assigned_patients = PatientModel.get_assigned_to_doctor(doctor_id)

    # Get Recent Activity & Audit Logs for this doctor
    recent_activity = AuditService.get_logs(limit=6, user_filter=session['user_id'])

    # Medical Records recorded
    medical_records = RecordModel.get_all_medical_records()

    # Active Emergency Access Grants
    all_emergencies = RecordModel.get_all_emergency_access()
    active_emergencies = [e for e in all_emergencies if e['doctor_id'] == doctor_id and e['is_active']]

    return render_template(
        'doctor_dashboard.html',
        user=user,
        doctor=doc,
        risk=risk,
        patients=assigned_patients,
        patient_count=len(assigned_patients),
        recent_activity=recent_activity,
        medical_records=medical_records[:5],
        active_emergencies=active_emergencies
    )

@doctor_bp.route('/records')
def medical_records_view():
    user = UserModel.get_by_user_id(session['user_id'])
    doc = UserModel.get_doctor_by_user_id(session['user_id'])
    doctor_id = doc['doctor_id'] if doc else 'D001'

    all_records = RecordModel.get_all_medical_records()

    AuditService.log(
        user_id=session['user_id'],
        role='doctor',
        action='VIEW_MEDICAL_RECORDS',
        ip_address=request.remote_addr or '127.0.0.1',
        device_status=session.get('device_status', 'TRUSTED'),
        risk_score=session.get('risk_score', 10),
        risk_level=session.get('risk_level', 'LOW'),
        result='SUCCESS',
        session_id=session.get('session_id'),
        details='Doctor viewed clinical progress notes archive'
    )

    return render_template('medical_records.html', records=all_records, user=user, doctor=doc)

@doctor_bp.route('/confidential-records')
def confidential_records_view():
    user = UserModel.get_by_user_id(session['user_id'])
    doc = UserModel.get_doctor_by_user_id(session['user_id'])
    doctor_id = doc['doctor_id'] if doc else 'D001'
    doc_permission = doc['permission_level'] if doc else 'NORMAL'

    all_confidential = RecordModel.get_all_confidential_records()

    # Tag records with accessibility based on sensitivity level
    annotated = []
    for r in all_confidential:
        item = dict(r)
        allowed = PatientModel.can_access_sensitivity(doc_permission, r['sensitivity_level'])
        # Also check if doctor is assigned or has emergency access
        is_assigned = PatientModel.is_assigned(doctor_id, r['patient_id']) or PatientModel.has_emergency_access(doctor_id, r['patient_id'])
        item['can_view'] = allowed and is_assigned
        annotated.append(item)

    AuditService.log(
        user_id=session['user_id'],
        role='doctor',
        action='VIEW_CONFIDENTIAL_CATALOG',
        ip_address=request.remote_addr or '127.0.0.1',
        device_status=session.get('device_status', 'TRUSTED'),
        risk_score=session.get('risk_score', 15),
        risk_level=session.get('risk_level', 'LOW'),
        result='SUCCESS',
        session_id=session.get('session_id'),
        details=f"Doctor {doctor_id} queried confidential records registry. Permission: {doc_permission}"
    )

    return render_template('confidential_records.html', records=annotated, user=user, doctor=doc)

@doctor_bp.route('/emergency-access', methods=['GET', 'POST'])
def emergency_access():
    user = UserModel.get_by_user_id(session['user_id'])
    doc = UserModel.get_doctor_by_user_id(session['user_id'])
    doctor_id = doc['doctor_id'] if doc else 'D001'

    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        reason = request.form.get('reason', '').strip()

        if not patient_id or not reason:
            flash("⚠️ Patient ID and clinical justification reason are mandatory.", "warning")
            return redirect(url_for('doctor.emergency_access'))

        patient = PatientModel.get_by_id(patient_id)
        if not patient:
            flash("Patient record not found in system.", "danger")
            return redirect(url_for('doctor.emergency_access'))

        # Calculate Risk before and with emergency factor (+15)
        risk_before = session.get('risk_score', 10)
        risk_after = min(100, risk_before + 15)

        # Grant expires in 15 minutes
        expires_at = (datetime.now() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')

        RecordModel.create_emergency_access(
            doctor_id=doctor_id,
            patient_id=patient_id,
            session_id=session.get('session_id', 'SESS-EMERGENCY'),
            reason=reason,
            expires_at=expires_at,
            risk_before=risk_before,
            risk_after=risk_after
        )

        AuditService.log(
            user_id=session['user_id'],
            role='doctor',
            action='EMERGENCY_ACCESS',
            patient_id=patient_id,
            ip_address=request.remote_addr or '127.0.0.1',
            device_status=session.get('device_status', 'TRUSTED'),
            risk_score=risk_after,
            risk_level='LOW' if risk_after <= 30 else 'MEDIUM',
            result='SUCCESS',
            threat_type='EMERGENCY_BREAK_GLASS',
            session_id=session.get('session_id'),
            details=f"Emergency Break-Glass access granted for Doctor {doctor_id} on patient {patient_id}. Reason: {reason}"
        )

        ThreatDetector.analyze_event(
            user_id=session['user_id'],
            action='EMERGENCY_ACCESS',
            risk_score=risk_after,
            details=f"Emergency Break-Glass activated by Dr. {doc['name']} for patient {patient_id}. Justification: {reason}",
            threat_type='Emergency Break-Glass Access',
            severity='MEDIUM'
        )

        flash(f"🚨 EMERGENCY BREAK-GLASS APPROVED: 15-minute access granted for patient {patient_id}.", "warning")
        return redirect(url_for('patients.patient_detail', patient_id=patient_id))

    all_emergencies = RecordModel.get_all_emergency_access()
    all_patients = PatientModel.get_all()

    return render_template(
        'emergency_access.html',
        user=user,
        doctor=doc,
        emergencies=all_emergencies,
        patients=all_patients
    )
