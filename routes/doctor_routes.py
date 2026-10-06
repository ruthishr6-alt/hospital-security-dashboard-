from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.patient import Patient
from services.auth_service import AuthService
from services.risk_engine import RiskEngine
from services.audit_service import AuditService

doctor_bp = Blueprint('doctor', __name__)

def current_user():
    if 'user_id' not in session:
        return None
    return AuthService.get_user_by_id(session['user_id'])

@doctor_bp.before_request
def check_doctor_auth():
    if request.endpoint and 'static' not in request.endpoint:
        if 'user_id' not in session:
            flash("Please authenticate to access clinical cardiology services.", 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') not in ('doctor', 'admin'):
            flash("Unauthorized access. Clinical credentials required.", 'danger')
            return redirect(url_for('auth.login'))

@doctor_bp.route('/doctor/dashboard')
def dashboard():
    user = current_user()
    doctor_id = user['user_id']
    
    # Calculate session risk
    risk_eval = RiskEngine.evaluate_request(
        user=user,
        request_obj=request,
        resource_name='DOCTOR_DASHBOARD'
    )
    
    # Audit log
    AuditService.log(
        action='VIEW_DOCTOR_DASHBOARD',
        risk_result=risk_eval,
        user=user,
        request_obj=request,
        resource='DOCTOR_PORTAL',
        details=f"Doctor {user['name']} opened clinical dashboard"
    )

    # Get authorized patients assigned to this doctor
    assigned_patients = Patient.get_assigned_to_doctor(doctor_id)
    
    # Summary vitals & alerts
    critical_cases = sum(1 for p in assigned_patients if p.get('condition_severity') == 'CRITICAL')
    severe_cases = sum(1 for p in assigned_patients if p.get('condition_severity') == 'SEVERE')

    return render_template(
        'doctor_dashboard.html',
        user=user,
        patients=assigned_patients,
        critical_count=critical_cases,
        severe_count=severe_cases,
        total_assigned=len(assigned_patients),
        risk_eval=risk_eval
    )

@doctor_bp.route('/doctor/patients')
def patient_list():
    user = current_user()
    doctor_id = user['user_id']
    query_str = request.args.get('q', '').strip()

    # Calculate access risk
    risk_eval = RiskEngine.evaluate_request(
        user=user,
        request_obj=request,
        resource_name='PATIENT_LIST'
    )

    if query_str:
        patients = Patient.search_real(query_str, doctor_user_id=doctor_id if user['role'] == 'doctor' else None)
        action_note = f"Doctor searched authorized patients with term: '{query_str}'"
    else:
        patients = Patient.get_assigned_to_doctor(doctor_id) if user['role'] == 'doctor' else Patient.get_all_real()
        action_note = "Doctor viewed assigned patient catalog"

    AuditService.log(
        action='QUERY_PATIENT_LIST',
        risk_result=risk_eval,
        user=user,
        request_obj=request,
        resource='PATIENT_REGISTRY',
        details=action_note
    )

    return render_template(
        'patient_list.html',
        user=user,
        patients=patients,
        query_str=query_str,
        risk_eval=risk_eval
    )
