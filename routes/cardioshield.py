import os
import uuid
from datetime import datetime, timedelta
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
from services.authorization_service import AuthorizationService
from services.photo_service import PhotoService
from services.phone_service import PhoneService
from services.ehr_service import EhrService
from werkzeug.security import generate_password_hash

cardioshield_bp = Blueprint('cardioshield', __name__)

# Helper to check login
def require_login():
    if 'user_id' not in session:
        flash("Please log in to access this page.", "warning")
        return False
    return True

# Helper to check admin
def is_admin():
    return session.get('role') == 'admin'

# =========================================================================
# 1. HOME & ABOUT
# =========================================================================

@cardioshield_bp.route('/about')
def about_page():
    return redirect(url_for('home') + '#about')

# =========================================================================
# 2. DASHBOARD (MAIN SECURITY OVERVIEW)
# =========================================================================

@cardioshield_bp.route('/dashboard')
def dashboard():
    if not require_login():
        return redirect(url_for('auth.login'))

    user = UserModel.get_by_user_id(session['user_id'])
    doc = UserModel.get_doctor_by_user_id(session['user_id']) if user and user['role'] == 'doctor' else None

    # Overview Metrics Cards
    total_doctors = query_db("SELECT COUNT(*) as cnt FROM doctors", one=True)['cnt'] or 0
    total_patients = query_db("SELECT COUNT(*) as cnt FROM patients WHERE is_decoy = 0", one=True)['cnt'] or 0
    active_sessions = query_db("SELECT COUNT(*) as cnt FROM sessions WHERE is_active = 1", one=True)['cnt'] or 3
    security_alerts_count = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE status != 'RESOLVED'", one=True)['cnt'] or 0
    critical_risk_events = query_db("SELECT COUNT(*) as cnt FROM risk_events WHERE risk_level IN ('HIGH', 'CRITICAL')", one=True)['cnt'] or 0
    decoy_sessions_count = query_db("SELECT COUNT(*) as cnt FROM decoy_sessions", one=True)['cnt'] or 0
    recent_threats_count = query_db("SELECT COUNT(*) as cnt FROM security_alerts WHERE severity IN ('HIGH', 'CRITICAL')", one=True)['cnt'] or 0

    overview_metrics = {
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'active_sessions': active_sessions,
        'security_alerts': security_alerts_count,
        'critical_risk_events': critical_risk_events,
        'decoy_sessions': decoy_sessions_count,
        'recent_threats': recent_threats_count
    }

    # Recent Alerts & Threats
    recent_alerts = query_db("SELECT * FROM security_alerts ORDER BY timestamp DESC LIMIT 6")
    recent_logs = AuditService.get_logs(limit=6)
    threat_stats = ThreatDetector.get_summary_stats()

    return render_template(
        'dashboard.html',
        user=user,
        doctor=doc,
        metrics=overview_metrics,
        recent_alerts=recent_alerts,
        recent_logs=recent_logs,
        threat_stats=threat_stats
    )

# =========================================================================
# 3. DEDICATED SECURITY TOOL PAGES
# =========================================================================

# A. Advanced Healthcare Security
@cardioshield_bp.route('/advanced-security')
def advanced_security():
    user = UserModel.get_by_user_id(session.get('user_id'))
    threat_stats = ThreatDetector.get_summary_stats()
    return render_template('advanced_security.html', user=user, threat_stats=threat_stats)

# B. Security Alerts
@cardioshield_bp.route('/security-alerts')
def security_alerts_view():
    if not require_login():
        return redirect(url_for('auth.login'))

    user = UserModel.get_by_user_id(session['user_id'])
    status_filter = request.args.get('status')
    severity_filter = request.args.get('severity')

    alerts = AlertService.get_all_alerts(status_filter, severity_filter)
    threat_stats = ThreatDetector.get_summary_stats()

    return render_template(
        'security_alerts.html',
        user=user,
        alerts=alerts,
        stats=threat_stats,
        status_filter=status_filter,
        severity_filter=severity_filter
    )

# C. Risk Analysis
# (Already defined in routes/security.py, but alias here ensures consistent availability)
@cardioshield_bp.route('/security/risk-analysis-view')
def risk_analysis_view():
    return redirect(url_for('security.risk_analysis'))

# D. Threat Monitoring
@cardioshield_bp.route('/threat-monitoring')
def threat_monitoring_view():
    if not require_login():
        return redirect(url_for('auth.login'))

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

    # Security event categories
    failed_logins = query_db("SELECT COUNT(*) as c FROM audit_logs WHERE action LIKE '%LOGIN_FAILED%'", one=True)['c'] or 0
    unauthorized_probes = query_db("SELECT COUNT(*) as c FROM audit_logs WHERE result IN ('DENIED', 'DECOY_SERVED')", one=True)['c'] or 0
    bulk_access = query_db("SELECT COUNT(*) as c FROM audit_logs WHERE action LIKE '%BULK%' OR details LIKE '%rapid%'", one=True)['c'] or 0
    unknown_devices = query_db("SELECT COUNT(*) as c FROM audit_logs WHERE device_status = 'UNKNOWN'", one=True)['c'] or 0
    insider_threats = stats.get('insider_threats', 0)
    admin_probes = query_db("SELECT COUNT(*) as c FROM audit_logs WHERE details LIKE '%admin%' AND result = 'DENIED'", one=True)['c'] or 0

    return render_template(
        'threat_monitor.html',
        user=user,
        stats=stats,
        threat_events=threat_events,
        top_sources=top_threat_sources,
        threat_breakdown={
            'failed_logins': failed_logins,
            'unauthorized_probes': unauthorized_probes,
            'bulk_access': bulk_access,
            'unknown_devices': unknown_devices,
            'insider_threats': insider_threats,
            'admin_probes': admin_probes
        }
    )

# E. Decoy Environment
@cardioshield_bp.route('/decoy-environment')
def decoy_environment_view():
    decoy_patients = DeceptionService.get_all_decoy_patients()
    user = UserModel.get_by_user_id(session.get('user_id'))
    
    DeceptionService.record_decoy_interaction(
        user_id=session.get('user_id', 'SUSPICIOUS_CLIENT'),
        ip_address=request.remote_addr or '127.0.0.1',
        fake_patient_id='CATALOG_BROWSE',
        action_performed='DECOY_CATALOG_EXPLORATION',
        risk_score=session.get('risk_score', 85),
        threat_level=session.get('risk_level', 'CRITICAL')
    )

    return render_template('decoy.html', patients=decoy_patients, user=user)

# F. Decoy Activity Monitor
@cardioshield_bp.route('/decoy-monitor')
def decoy_monitor_view():
    if not require_login():
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

# G. Audit Logs
@cardioshield_bp.route('/audit-logs')
def audit_logs_view():
    if not require_login():
        return redirect(url_for('auth.login'))

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

# H. Device Security
@cardioshield_bp.route('/device-security')
def device_security_view():
    if not require_login():
        return redirect(url_for('auth.login'))

    user = UserModel.get_by_user_id(session['user_id'])
    devices = UserModel.get_all_devices()
    return render_template('device_security.html', user=user, devices=devices)

# I. Emergency Break-Glass Protocol
@cardioshield_bp.route('/break-glass', methods=['GET', 'POST'])
def break_glass_view():
    if not require_login():
        return redirect(url_for('auth.login'))

    user = UserModel.get_by_user_id(session['user_id'])
    doc = UserModel.get_doctor_by_user_id(session['user_id'])
    doctor_id = doc['doctor_id'] if doc else (session.get('doctor_id') or 'D001')

    if request.method == 'POST':
        patient_id = request.form.get('patient_id', '').strip()
        reason = request.form.get('reason', '').strip()

        if not patient_id or not reason:
            flash("Patient ID and Clinical Justification are required for emergency override.", "danger")
            return redirect(url_for('cardioshield.break_glass_view'))

        # Check existing real patient
        target_patient = PatientModel.get_by_id(patient_id)
        if not target_patient:
            flash(f"Patient {patient_id} not found in database.", "danger")
            return redirect(url_for('cardioshield.break_glass_view'))

        # Pre/Post risk calculation
        risk_before = session.get('risk_score', 10)
        risk_after = min(risk_before + 15, 100)
        session_id = session.get('session_id', f"SESS-{session['user_id'][:6]}")

        expires_at = (datetime.utcnow() + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')

        execute_db('''
            INSERT INTO emergency_access (doctor_id, patient_id, session_id, reason, expires_at, risk_score_before, risk_score_after, approved, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'ACTIVE')
        ''', (doctor_id, patient_id, session_id, reason, expires_at, risk_before, risk_after))

        # Log audit entry
        AuditService.log(
            user_id=session['user_id'],
            role=session.get('role', 'doctor'),
            patient_id=patient_id,
            action='EMERGENCY_BREAK_GLASS_ACTIVATED',
            ip_address=request.remote_addr or '127.0.0.1',
            device_status=session.get('device_status', 'TRUSTED'),
            risk_score=risk_after,
            risk_level='MEDIUM',
            result='GRANTED',
            session_id=session_id,
            threat_type='BREAK_GLASS_OVERRIDE',
            details=f"15-Minute Emergency Break-Glass granted for {patient_id}. Reason: {reason}"
        )

        flash(f"⚡ Emergency Break-Glass access granted for Patient {patient_id} (15 minutes).", "warning")
        return redirect(url_for('patients.patient_detail', patient_id=patient_id))

    # GET: List active and past break-glass requests
    all_grants = RecordModel.get_all_emergency_access()
    patients = PatientModel.get_all()

    return render_template(
        'emergency_access.html',
        user=user,
        doctor=doc,
        doctor_id=doctor_id,
        grants=all_grants,
        patients=patients
    )

# =========================================================================
# 4. DOCTORS SECTION (LIST, CREATE, DETAILS, EDIT, DELETE)
# =========================================================================

@cardioshield_bp.route('/doctors')
def doctor_list():
    query_str = request.args.get('q', '').strip()
    doctors = UserModel.get_all_doctors()

    for d in doctors:
        cnt = query_db("SELECT count(*) as c FROM doctor_patient_assignments WHERE doctor_id = ? AND status = 'ACTIVE'", (d['doctor_id'],), one=True)
        d['patient_count'] = cnt['c'] if cnt else 0

    if query_str:
        q_lower = query_str.lower()
        doctors = [d for d in doctors if q_lower in d['name'].lower() or q_lower in (d.get('specialization') or '').lower() or q_lower in d['doctor_id'].lower() or q_lower in (d.get('department') or '').lower()]

    user = UserModel.get_by_user_id(session.get('user_id'))
    return render_template('doctor_list.html', doctors=doctors, query_str=query_str, user=user)

@cardioshield_bp.route('/doctors/new', methods=['GET', 'POST'])
def doctor_create():
    if request.method == 'GET':
        user = UserModel.get_by_user_id(session.get('user_id'))
        generated_id = UserModel.generate_unique_doctor_id()
        return render_template('doctor_new.html', user=user, generated_id=generated_id)

    # POST: Process new doctor
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    doctor_id = request.form.get('doctor_id', '').strip().upper()
    specialization = request.form.get('specialization', '').strip()
    qualification = request.form.get('qualification', 'MBBS, MD Cardiology').strip()
    experience = request.form.get('experience', '8 Years').strip()
    department = request.form.get('department', 'Cardiology').strip()
    permission_level = request.form.get('permission_level', 'NORMAL').strip()
    account_status = request.form.get('account_status', 'active').strip()

    country_code = request.form.get('country_code', '+1').strip()
    local_phone = request.form.get('phone_number', '').strip()

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    # Field Validations
    if not name or not specialization or not department:
        flash("Please provide all required fields: Full Name, Specialization, and Department.", "danger")
        return redirect(url_for('cardioshield.doctor_create'))

    if email and ('@' not in email or '.' not in email):
        flash("Please enter a valid email address.", "danger")
        return redirect(url_for('cardioshield.doctor_create'))

    if not doctor_id:
        doctor_id = UserModel.generate_unique_doctor_id()
    else:
        # Check uniqueness
        if query_db("SELECT id FROM doctors WHERE doctor_id = ?", (doctor_id,), one=True):
            flash(f"Doctor ID '{doctor_id}' is already assigned. A unique ID has been generated.", "warning")
            doctor_id = UserModel.generate_unique_doctor_id()

    # Phone handling
    if local_phone:
        full_phone = PhoneService.format_phone(country_code, local_phone) if not local_phone.startswith('+') else local_phone
        is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
        if not is_valid:
            flash(f"Phone validation notice: {p_err}", "warning")
        demo_phone = validated_phone or full_phone
    else:
        demo_phone = '+1 (555) 019-2834'

    # Photo handling
    photo_file = request.files.get('profile_photo')
    photo_filename = None
    if photo_file and photo_file.filename:
        photo_filename, err = PhotoService.validate_and_save(photo_file, 'doctor')
        if err:
            flash(f"Photo upload issue: {err}. Using default avatar.", "warning")

    # Username and password setup
    if not username:
        username = f"doc_{doctor_id.lower()}"
    if UserModel.get_by_username(username):
        username = f"doc_{doctor_id.lower()}_{uuid.uuid4().hex[:4]}"
    if not password:
        password = 'DoctorDemo#2026!'

    password_hash = generate_password_hash(password)

    # Save to database permanently
    try:
        user_uid = f"USR-{uuid.uuid4().hex[:8].upper()}"
        UserModel.create_doctor(
            doctor_id=doctor_id,
            name=name,
            specialization=specialization,
            qualification=qualification,
            experience=experience,
            department=department,
            demo_phone=demo_phone,
            email=email or f"{doctor_id.lower()}@cardioshield-hospital.org",
            permission_level=permission_level,
            status=account_status,
            profile_photo=photo_filename,
            username=username,
            password_hash=password_hash,
            user_id=user_uid
        )

        # Audit log entry
        AuditService.log(
            user_id=session.get('user_id', user_uid),
            role=session.get('role', 'doctor'),
            action='DOCTOR_PROFILE_CREATED',
            ip_address=request.remote_addr or '127.0.0.1',
            device_status=session.get('device_status', 'TRUSTED'),
            risk_score=10,
            risk_level='LOW',
            result='SUCCESS',
            details=f"Created Doctor profile {doctor_id} ({name}, {specialization}) permanently stored in database."
        )

        flash(f"Doctor profile for {name} ({doctor_id}) created and saved successfully!", "success")
        return redirect(url_for('cardioshield.doctor_detail', doctor_id=doctor_id))
    except Exception as e:
        flash(f"Error creating doctor: {str(e)}", "danger")
        return redirect(url_for('cardioshield.doctor_create'))

@cardioshield_bp.route('/doctors/<doctor_id>')
def doctor_detail(doctor_id):
    doctor = UserModel.get_doctor_by_doctor_id(doctor_id)
    if not doctor:
        flash(f"Doctor {doctor_id} not found.", "danger")
        return redirect(url_for('cardioshield.doctor_list'))

    user = UserModel.get_by_user_id(session.get('user_id'))
    assigned_patients = PatientModel.get_assigned_to_doctor(doctor_id)

    # Recent Audit Activity for this doctor
    recent_activity = AuditService.get_logs(limit=10, user_filter=doctor.get('user_id'))

    # Device Status
    device_info = UserModel.get_device(f"DEV-{doctor_id}-STATION") or UserModel.get_device('DEV-DOC01-TRUSTED')

    return render_template(
        'doctor_detail.html',
        doctor=doctor,
        assigned_patients=assigned_patients,
        recent_activity=recent_activity,
        device=device_info,
        user=user
    )

@cardioshield_bp.route('/doctors/<doctor_id>/edit', methods=['GET', 'POST'])
def doctor_edit(doctor_id):
    if not require_login():
        return redirect(url_for('auth.login'))

    doctor = UserModel.get_doctor_by_doctor_id(doctor_id)
    if not doctor:
        flash(f"Doctor {doctor_id} not found.", "danger")
        return redirect(url_for('cardioshield.doctor_list'))

    # Security check: Admin can edit any; Doctor can edit own profile
    current_u = UserModel.get_by_user_id(session['user_id'])
    is_authorized = is_admin() or (current_u and current_u['role'] == 'doctor' and session.get('doctor_id') == doctor_id)
    if not is_authorized:
        flash("Unauthorized: You may only modify your own clinical profile.", "danger")
        return redirect(url_for('cardioshield.doctor_detail', doctor_id=doctor_id))

    if request.method == 'GET':
        return render_template('doctor_edit.html', doctor=doctor, user=current_u)

    # POST: Update
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    specialization = request.form.get('specialization', '').strip()
    qualification = request.form.get('qualification', '').strip()
    experience = request.form.get('experience', '').strip()
    department = request.form.get('department', '').strip()
    demo_phone = request.form.get('demo_phone', '').strip()
    permission_level = request.form.get('permission_level', doctor['permission_level']).strip() if is_admin() else doctor['permission_level']
    status = request.form.get('status', doctor['status']).strip() if is_admin() else doctor['status']

    # Photo handling
    photo_file = request.files.get('profile_photo')
    new_photo = None
    if photo_file and photo_file.filename:
        new_photo, err = PhotoService.validate_and_save(photo_file, 'doctor')
        if err:
            flash(f"Photo update warning: {err}", "warning")

    remove_photo = request.form.get('remove_photo') == '1'
    if remove_photo:
        UserModel.remove_doctor_photo(doctor_id)
        new_photo = None

    UserModel.update_doctor_profile(
        doctor_id=doctor_id,
        name=name,
        specialization=specialization,
        qualification=qualification,
        experience=experience,
        department=department,
        demo_phone=demo_phone,
        permission_level=permission_level,
        status=status,
        email=email,
        profile_photo=new_photo if (new_photo or remove_photo) else None
    )

    AuditService.log(
        user_id=session['user_id'],
        role=session.get('role', 'doctor'),
        action='DOCTOR_PROFILE_UPDATED',
        ip_address=request.remote_addr or '127.0.0.1',
        device_status=session.get('device_status', 'TRUSTED'),
        risk_score=10,
        risk_level='LOW',
        result='SUCCESS',
        details=f"Doctor profile {doctor_id} ({name}) updated permanently in database."
    )

    flash(f"Doctor profile for {name} updated successfully.", "success")
    return redirect(url_for('cardioshield.doctor_detail', doctor_id=doctor_id))

@cardioshield_bp.route('/doctors/<doctor_id>/delete', methods=['POST'])
def doctor_delete(doctor_id):
    if not require_login():
        return redirect(url_for('auth.login'))

    if not is_admin():
        flash("⛔ Admin clearance required to delete doctor accounts.", "danger")
        return redirect(url_for('cardioshield.doctor_detail', doctor_id=doctor_id))

    deleted = UserModel.delete_doctor(doctor_id)
    if deleted:
        AuditService.log(
            user_id=session['user_id'],
            role='admin',
            action='DOCTOR_ACCOUNT_DELETED',
            ip_address=request.remote_addr or '127.0.0.1',
            device_status='TRUSTED',
            risk_score=20,
            risk_level='LOW',
            result='SUCCESS',
            details=f"Administrator removed Doctor {doctor_id} ({deleted['name']}) and associated credentials."
        )
        flash(f"Doctor {doctor_id} ({deleted['name']}) has been deleted successfully.", "info")
    else:
        flash(f"Doctor {doctor_id} not found.", "warning")

    return redirect(url_for('cardioshield.doctor_list'))

# =========================================================================
# 5. PATIENTS SECTION (CREATE, EDIT, DELETE, DETAILS ALIAS)
# =========================================================================

@cardioshield_bp.route('/patients/new', methods=['GET', 'POST'])
def patient_create():
    doctors = UserModel.get_all_doctors()
    user = UserModel.get_by_user_id(session.get('user_id'))

    if request.method == 'GET':
        generated_id = PatientModel.generate_unique_patient_id()
        return render_template('patient_new.html', user=user, doctors=doctors, generated_id=generated_id)

    # POST: Process new patient
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    age_str = request.form.get('age', '52').strip()
    gender = request.form.get('gender', 'Male').strip()
    blood_group = request.form.get('blood_group', 'O+').strip()
    patient_id = request.form.get('patient_id', '').strip().upper()
    assigned_doctor_id = request.form.get('assigned_doctor_id', 'D001').strip()
    heart_condition_category = request.form.get('heart_condition_category', '').strip()
    medical_history = request.form.get('medical_history', '').strip() or 'Synthetic Cardiology History: Coronary Artery Disease, Hypertension.'
    emergency_contact = request.form.get('emergency_contact', '').strip()
    record_sensitivity = request.form.get('record_sensitivity', 'NORMAL').strip()
    access_status = request.form.get('access_status', 'active').strip()

    country_code = request.form.get('country_code', '+1').strip()
    local_phone = request.form.get('phone_number', '').strip()

    # Validations
    if not name or not heart_condition_category or not emergency_contact:
        flash("Please fill in all mandatory fields: Full Name, Heart Condition, and Emergency Contact.", "danger")
        return redirect(url_for('cardioshield.patient_create'))

    try:
        age = int(age_str)
        if age < 1 or age > 120:
            raise ValueError()
    except ValueError:
        flash("Please enter a valid age between 1 and 120.", "danger")
        return redirect(url_for('cardioshield.patient_create'))

    if not patient_id:
        patient_id = PatientModel.generate_unique_patient_id()
    else:
        if query_db("SELECT id FROM patients WHERE patient_id = ?", (patient_id,), one=True):
            flash(f"Patient ID '{patient_id}' already exists. Assigned new unique ID.", "warning")
            patient_id = PatientModel.generate_unique_patient_id()

    # Phone handling
    if local_phone:
        full_phone = PhoneService.format_phone(country_code, local_phone) if not local_phone.startswith('+') else local_phone
        is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
        if not is_valid:
            flash(f"Phone format note: {p_err}", "warning")
        phone_number = validated_phone or full_phone
    else:
        phone_number = '+1 (555) 019-1001'

    # Photo handling
    photo_file = request.files.get('profile_photo')
    photo_filename = None
    if photo_file and photo_file.filename:
        photo_filename, err = PhotoService.validate_and_save(photo_file, 'patient')
        if err:
            flash(f"Photo upload issue: {err}. Using default avatar.", "warning")

    # Sample synthetic clinical reports
    ecg_report = f"Normal Sinus Rhythm with mild ST elevation consistent with {heart_condition_category}. PR: 160ms, QRS: 90ms, QTc: 420ms."
    echo_report = "LVEF 50-55%. Normal ventricular wall motion. Mild aortic sclerosis without hemodynamic significance."
    blood_test_report = "Troponin-I: 0.02 ng/mL (Normal) | BNP: 85 pg/mL | K+: 4.1 mEq/L | Creatinine: 0.9 mg/dL."
    prescriptions = '[{"drug":"Aspirin (Chewable)","dose":"81 mg","route":"Oral","frequency":"Once Daily"},{"drug":"Atorvastatin","dose":"40 mg","route":"Oral","frequency":"At Bedtime"}]'
    vitals = 'HR: 72 bpm | BP: 122/78 mmHg | SpO2: 99% | Rhythm: Sinus'

    try:
        PatientModel.create_patient(
            patient_id=patient_id,
            name=name,
            age=age,
            blood_group=blood_group,
            gender=gender,
            assigned_doctor_id=assigned_doctor_id,
            heart_condition_category=heart_condition_category,
            medical_history=medical_history,
            ecg_report=ecg_report,
            echo_report=echo_report,
            blood_test_report=blood_test_report,
            current_prescriptions=prescriptions,
            emergency_contact=emergency_contact,
            record_sensitivity_level=record_sensitivity,
            vitals=vitals,
            profile_photo=photo_filename,
            status=access_status,
            phone_number=phone_number,
            email=email or f"{patient_id.lower()}@synthetic-heart.org"
        )

        AuditService.log(
            user_id=session.get('user_id', 'CLINICIAN_USER'),
            role=session.get('role', 'doctor'),
            patient_id=patient_id,
            action='PATIENT_PROFILE_CREATED',
            ip_address=request.remote_addr or '127.0.0.1',
            device_status=session.get('device_status', 'TRUSTED'),
            risk_score=10,
            risk_level='LOW',
            result='SUCCESS',
            details=f"Synthetic Patient profile {patient_id} ({name}) created and permanently saved to database."
        )

        flash(f"Patient profile {patient_id} ({name}) created successfully!", "success")
        return redirect(url_for('patients.patient_detail', patient_id=patient_id))
    except Exception as e:
        flash(f"Error creating patient: {str(e)}", "danger")
        return redirect(url_for('cardioshield.patient_create'))

@cardioshield_bp.route('/patients/<patient_id>')
def patient_detail_view(patient_id):
    # Delegate to patients_bp.patient_detail to preserve full Zero-Trust logic & Decoy traps
    return redirect(url_for('patients.patient_detail', patient_id=patient_id))

@cardioshield_bp.route('/patients/<patient_id>/edit', methods=['GET', 'POST'])
def patient_edit(patient_id):
    if not require_login():
        return redirect(url_for('auth.login'))

    patient = PatientModel.get_by_id(patient_id)
    if not patient:
        flash(f"Patient {patient_id} not found.", "danger")
        return redirect(url_for('patients.patient_list'))

    doctors = UserModel.get_all_doctors()
    user = UserModel.get_by_user_id(session['user_id'])

    if request.method == 'GET':
        return render_template('patient_edit.html', patient=patient, doctors=doctors, user=user)

    # POST: Update
    name = request.form.get('name', patient['name']).strip()
    age = int(request.form.get('age', patient['age']))
    gender = request.form.get('gender', patient['gender']).strip()
    blood_group = request.form.get('blood_group', patient['blood_group']).strip()
    assigned_doctor_id = request.form.get('assigned_doctor_id', patient['assigned_doctor_id']).strip()
    heart_condition_category = request.form.get('heart_condition_category', patient['heart_condition_category']).strip()
    medical_history = request.form.get('medical_history', patient['medical_history']).strip()
    emergency_contact = request.form.get('emergency_contact', patient['emergency_contact']).strip()
    phone_number = request.form.get('phone_number', patient['phone_number']).strip()
    record_sensitivity_level = request.form.get('record_sensitivity_level', patient['record_sensitivity_level']).strip()
    status = request.form.get('status', patient['status']).strip()

    # Photo handling
    photo_file = request.files.get('profile_photo')
    new_photo = None
    if photo_file and photo_file.filename:
        new_photo, err = PhotoService.validate_and_save(photo_file, 'patient')
        if err:
            flash(f"Photo error: {err}", "warning")

    if request.form.get('remove_photo') == '1':
        PatientModel.remove_patient_photo(patient_id)
        new_photo = None

    PatientModel.update_patient(
        patient_id=patient_id,
        name=name,
        age=age,
        blood_group=blood_group,
        gender=gender,
        assigned_doctor_id=assigned_doctor_id,
        heart_condition_category=heart_condition_category,
        medical_history=medical_history,
        ecg_report=patient['ecg_report'],
        echo_report=patient['echo_report'],
        blood_test_report=patient['blood_test_report'],
        current_prescriptions=json.dumps(patient['current_prescriptions']) if isinstance(patient['current_prescriptions'], list) else str(patient['current_prescriptions']),
        emergency_contact=emergency_contact,
        record_sensitivity_level=record_sensitivity_level,
        status=status,
        profile_photo=new_photo if (new_photo or request.form.get('remove_photo') == '1') else None,
        phone_number=phone_number
    )

    AuditService.log(
        user_id=session['user_id'],
        role=session.get('role', 'doctor'),
        patient_id=patient_id,
        action='PATIENT_PROFILE_UPDATED',
        ip_address=request.remote_addr or '127.0.0.1',
        device_status=session.get('device_status', 'TRUSTED'),
        risk_score=10,
        risk_level='LOW',
        result='SUCCESS',
        details=f"Patient {patient_id} ({name}) clinical profile updated in database."
    )

    flash(f"Patient {name} ({patient_id}) updated successfully.", "success")
    return redirect(url_for('patients.patient_detail', patient_id=patient_id))

@cardioshield_bp.route('/patients/<patient_id>/delete', methods=['POST'])
def patient_delete(patient_id):
    if not require_login():
        return redirect(url_for('auth.login'))

    if not is_admin():
        flash("⛔ Admin clearance required to delete patient records.", "danger")
        return redirect(url_for('patients.patient_detail', patient_id=patient_id))

    deleted = PatientModel.delete_patient(patient_id)
    if deleted:
        AuditService.log(
            user_id=session['user_id'],
            role='admin',
            patient_id=patient_id,
            action='PATIENT_RECORD_DELETED',
            ip_address=request.remote_addr or '127.0.0.1',
            device_status='TRUSTED',
            risk_score=20,
            risk_level='LOW',
            result='SUCCESS',
            details=f"Administrator purged patient {patient_id} ({deleted['name']}) and associated clinical charts."
        )
        flash(f"Patient {patient_id} ({deleted['name']}) has been deleted successfully.", "info")
    else:
        flash(f"Patient {patient_id} not found.", "warning")

    return redirect(url_for('patients.patient_list'))

# =========================================================================
# 6. MEDICAL RECORDS – SECURE ACCESS PIPELINE
# =========================================================================

@cardioshield_bp.route('/medical-records', methods=['GET', 'POST'])
def medical_records_view():
    user = UserModel.get_by_user_id(session.get('user_id'))
    doc = UserModel.get_doctor_by_user_id(session.get('user_id')) if user and user['role'] == 'doctor' else None
    
    # All synthetic patients for the selector
    all_patients = PatientModel.get_all()
    selected_patient_id = request.args.get('patient_id') or request.form.get('patient_id')

    # If no patient selected, default to first or assigned
    if not selected_patient_id and all_patients:
        if doc:
            assigned = PatientModel.get_assigned_to_doctor(doc['doctor_id'])
            selected_patient_id = assigned[0]['patient_id'] if assigned else all_patients[0]['patient_id']
        else:
            selected_patient_id = all_patients[0]['patient_id']

    target_patient = PatientModel.get_by_id(selected_patient_id) if selected_patient_id else None

    # Run the 6-STEP SECURE ACCESS PIPELINE
    pipeline_result = None
    if target_patient:
        pipeline_result = evaluate_secure_access_pipeline(user, doc, target_patient, request)

    return render_template(
        'medical_records.html',
        user=user,
        doctor=doc,
        all_patients=all_patients,
        selected_patient_id=selected_patient_id,
        patient=target_patient,
        pipeline=pipeline_result
    )

def evaluate_secure_access_pipeline(user, doc, patient, req):
    """
    Executes the 6-Step Multi-Stage Secure Access Decision:
    STEP 1: Check login/session
    STEP 2: Check user role
    STEP 3: Check assignment/authorization (doctor assigned or emergency break-glass)
    STEP 4: Calculate risk score
    STEP 5: Check record sensitivity
    STEP 6: Decision (AUTHORIZED real record vs ACCESS DENIED / DECOY)
    """
    ip_address = req.headers.get('X-Forwarded-For', req.remote_addr or '127.0.0.1').split(',')[0].strip()
    device_id = session.get('device_id', 'DEV-DOC01-TRUSTED')
    device_status = session.get('device_status', 'TRUSTED')

    steps = []

    # STEP 1: Login / Session
    step1_passed = bool(user and session.get('user_id'))
    steps.append({
        'step_num': 1,
        'name': 'Session & Credential Authentication',
        'passed': step1_passed,
        'details': f"Session verified for UID: {user['user_id'] if user else 'ANONYMOUS'} ({device_status} hardware binding)" if step1_passed else "No active authenticated session detected."
    })

    # STEP 2: User Role
    role = user['role'] if user else 'unauthenticated'
    step2_passed = role in ['doctor', 'admin']
    steps.append({
        'step_num': 2,
        'name': 'Role-Based Authorization (RBAC)',
        'passed': step2_passed,
        'details': f"User role '{role.upper()}' holds clinical EMR viewing privileges." if step2_passed else f"Role '{role.upper()}' lacks clinical clearance."
    })

    # STEP 3: Patient-Specific Authorization
    is_assigned = False
    is_emergency = False
    step3_passed = False

    if user:
        if role == 'admin':
            step3_passed = True
            step3_details = "Administrator executive audit override."
        elif role == 'doctor' and doc:
            is_assigned = PatientModel.is_assigned(doc['doctor_id'], patient['patient_id'])
            is_emergency = PatientModel.has_emergency_access(doc['doctor_id'], patient['patient_id'])
            step3_passed = is_assigned or is_emergency
            if is_assigned:
                step3_details = f"Physician {doc['name']} is explicitly assigned to Patient {patient['patient_id']}."
            elif is_emergency:
                step3_details = f"Active Emergency Break-Glass override protocol in effect."
            else:
                step3_details = f"Physician {doc['name']} is NOT assigned to Patient {patient['patient_id']}."
        else:
            step3_details = "Non-clinician session."
    else:
        step3_details = "Unauthenticated probe."

    steps.append({
        'step_num': 3,
        'name': 'Patient-Specific Assignment & Clearance',
        'passed': step3_passed,
        'details': step3_details
    })

    # STEP 4: Risk Score Calculation
    risk = RiskEngine.calculate_risk(
        user=user,
        action='VIEW_PATIENT_RECORD' if step3_passed else 'UNAUTHORIZED_PATIENT_ACCESS',
        patient=patient,
        session_context={'ip_address': ip_address, 'device_id': device_id, 'device_status': device_status}
    )
    risk_score = risk['score']
    risk_level = risk['level']
    step4_passed = risk_score < 70
    steps.append({
        'step_num': 4,
        'name': 'Dynamic Risk Evaluation',
        'passed': step4_passed,
        'score': risk_score,
        'level': risk_level,
        'details': f"Risk Score: {risk_score}/100 ({risk_level}). Factors: {', '.join([r['factor'] for r in risk.get('reasons', [])[:2]]) or 'Normal Baseline'}"
    })

    # STEP 5: Record Sensitivity Clearance
    rec_sens = patient.get('record_sensitivity_level', 'NORMAL')
    doc_perm = doc['permission_level'] if doc else ('HIGHLY_CONFIDENTIAL' if role == 'admin' else 'NORMAL')
    step5_passed = PatientModel.can_access_sensitivity(doc_perm, rec_sens)
    steps.append({
        'step_num': 5,
        'name': 'Record Sensitivity Classification',
        'passed': step5_passed,
        'details': f"Record Tier: {rec_sens} vs Clinician Clearance: {doc_perm}. {'Clearance sufficient.' if step5_passed else 'Insufficient clearance for confidential chart.'}"
    })

    # STEP 6: Final Decision
    all_passed = step1_passed and step2_passed and step3_passed and step4_passed and step5_passed
    
    if all_passed:
        decision = 'AUTHORIZED'
        mode = 'PROTECTED_RECORD_SERVED'
        msg = "All 5 security controls passed. Real protected synthetic EHR rendered."
        
        # Log successful clinical access
        AuditService.log(
            user_id=user['user_id'],
            role=role,
            patient_id=patient['patient_id'],
            action='VIEW_MEDICAL_RECORD_AUTHORIZED',
            ip_address=ip_address,
            device_status=device_status,
            risk_score=risk_score,
            risk_level=risk_level,
            result='SUCCESS',
            details=f"Authorized clinical chart access for {patient['patient_id']} by {user['name']}"
        )
    else:
        decision = 'ACCESS_DENIED'
        mode = 'HONEYPOT_DECOY_ENGAGED'
        msg = "Security failure detected. Protected database shielded; session redirected to Decoy Honeypot."

        # Create security risk event
        execute_db('''
            INSERT INTO risk_events (user_id, session_id, action, factor_name, score_delta, new_score, risk_level, description)
            VALUES (?, ?, 'UNAUTHORIZED_MEDICAL_RECORD_PROBE', 'Access Control Violation', +35, ?, ?, ?)
        ''', (user['user_id'] if user else 'ANONYMOUS', session.get('session_id', 'SESS-SEC'), min(risk_score + 35, 100), 'HIGH' if risk_score >= 50 else 'CRITICAL',
              f"Unauthorized medical record probe targeting {patient['patient_id']}"))

        # Create security alert if high risk or unauthorized cross-patient
        if risk_score >= 60 or not step3_passed:
            alert_id = f"ALT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
            execute_db('''
                INSERT INTO security_alerts (alert_id, threat_type, severity, user_id, risk_score, description, status)
                VALUES (?, 'Unauthorized Patient Chart Probe', 'HIGH', ?, ?, ?, 'NEW')
            ''', (alert_id, user['user_id'] if user else 'ANONYMOUS', risk_score, f"Blocked unauthorized attempt to inspect patient {patient['patient_id']}"))

        # Log security denial / decoy
        AuditService.log(
            user_id=user['user_id'] if user else 'ANONYMOUS',
            role=role,
            patient_id=patient['patient_id'],
            action='VIEW_MEDICAL_RECORD_DENIED',
            ip_address=ip_address,
            device_status=device_status,
            risk_score=risk_score,
            risk_level=risk_level,
            result='DENIED',
            threat_type='UNAUTHORIZED_ACCESS_ATTEMPT',
            details=f"Blocked unauthorized medical record probe on {patient['patient_id']}. Shielded real data."
        )

        # Record decoy interaction
        DeceptionService.record_decoy_interaction(
            user_id=user['user_id'] if user else 'SUSPICIOUS_CLIENT',
            ip_address=ip_address,
            fake_patient_id=patient['patient_id'],
            action_performed='UNAUTHORIZED_CHART_INTERCEPTION',
            risk_score=risk_score,
            threat_level=risk_level
        )

    return {
        'decision': decision,
        'mode': mode,
        'message': msg,
        'steps': steps,
        'risk_score': risk_score,
        'risk_level': risk_level,
        'is_authorized': all_passed
    }
