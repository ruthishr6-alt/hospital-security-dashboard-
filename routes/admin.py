import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.db import query_db, execute_db
from models.user import UserModel
from models.patient import PatientModel
from models.record import RecordModel
from services.risk_engine import RiskEngine
from services.threat_detector import ThreatDetector
from services.deception_service import DeceptionService
from services.audit_service import AuditService
from services.photo_service import PhotoService
from services.phone_service import PhoneService
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
def verify_admin_auth():
    if request.endpoint and 'static' not in request.endpoint:
        if 'user_id' not in session:
            flash("Administrator clearance required.", "warning")
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            user = UserModel.get_by_user_id(session.get('user_id'))
            risk = RiskEngine.calculate_risk(user=user, action='ADMIN_PAGE_ACCESS')
            ThreatDetector.analyze_event(
                user_id=session.get('user_id'),
                action='ADMIN_PAGE_ACCESS',
                risk_score=risk['score'],
                details=f"Non-admin user {session.get('username')} probed admin endpoint",
                threat_type='Privilege Escalation Attempt',
                severity='HIGH'
            )
            flash("⛔ Access Denied: Administrator security clearance required.", "danger")
            return redirect(url_for('doctor.dashboard'))

@admin_bp.route('/admin/dashboard')
def dashboard():
    user = UserModel.get_by_user_id(session['user_id'])

    # 10 Executive Dashboard Cards
    total_doctors = query_db("SELECT COUNT(*) as cnt FROM doctors", one=True)['cnt']
    total_patients = query_db("SELECT COUNT(*) as cnt FROM patients", one=True)['cnt']
    active_sessions = query_db("SELECT COUNT(*) as cnt FROM sessions WHERE is_active = 1", one=True)['cnt'] or 3
    audit_stats = AuditService.get_summary_stats()
    threat_stats = ThreatDetector.get_summary_stats()
    decoy_stats = DeceptionService.get_stats()
    emergency_events = query_db("SELECT COUNT(*) as cnt FROM emergency_access", one=True)['cnt']

    cards = {
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'active_sessions': active_sessions,
        'failed_logins': audit_stats['failed_logins_count'],
        'blocked_attempts': audit_stats['blocked_count'],
        'suspicious_sessions': threat_stats['total_alerts'],
        'decoy_sessions': decoy_stats['total_decoy_sessions'],
        'critical_threats': threat_stats['critical_threats'],
        'emergency_access_events': emergency_events,
        'insider_threat_alerts': threat_stats['insider_threats'],
        'system_threat_level': threat_stats['threat_level'],
        'threat_color': threat_stats['threat_color']
    }

    recent_alerts = query_db("SELECT * FROM security_alerts ORDER BY timestamp DESC LIMIT 6")
    recent_decoys = DeceptionService.get_decoy_sessions(limit=5)
    recent_emergencies = RecordModel.get_all_emergency_access()[:4]

    # Fetch doctor cards and patient cards for the admin dashboard
    doctor_cards = UserModel.get_all_doctors()[:6]
    annotated_doc_cards = []
    for d in doctor_cards:
        d_dict = dict(d)
        r_row = query_db("SELECT current_score, risk_level FROM risk_scores WHERE user_id = ? ORDER BY id DESC LIMIT 1", (d['user_id'],), one=True)
        d_dict['risk_score'] = r_row['current_score'] if r_row else 10
        d_dict['risk_level'] = r_row['risk_level'] if r_row else 'LOW'
        d_dict['assigned_count'] = len(PatientModel.get_assigned_to_doctor(d['doctor_id']))
        annotated_doc_cards.append(d_dict)

    patient_cards = PatientModel.get_all()[:6]

    AuditService.log(
        user_id=session['user_id'],
        role='admin',
        action='VIEW_ADMIN_DASHBOARD',
        ip_address=request.remote_addr or '127.0.0.1',
        device_status=session.get('device_status', 'TRUSTED'),
        risk_score=5,
        risk_level='LOW',
        result='SUCCESS',
        session_id=session.get('session_id'),
        details='Administrator inspected SOC dashboard and live telemetry'
    )

    return render_template(
        'admin_dashboard.html',
        user=user,
        cards=cards,
        recent_alerts=recent_alerts,
        recent_decoys=recent_decoys,
        recent_emergencies=recent_emergencies,
        doctor_cards=annotated_doc_cards,
        patient_cards=patient_cards
    )

@admin_bp.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    user = UserModel.get_by_user_id(session['user_id'])

    if request.method == 'POST':
        action_type = request.form.get('action_type')

        if action_type == 'create_doctor':
            doctor_id = request.form.get('doctor_id', '').strip().upper()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            name = request.form.get('name', '').strip()
            specialization = request.form.get('specialization', '').strip() or request.form.get('specialty', '').strip()
            qualification = request.form.get('qualification', 'MBBS, MD Cardiology').strip()
            experience = request.form.get('experience', '5 Years').strip()
            department = request.form.get('department', 'Cardiology').strip()
            permission_level = request.form.get('permission_level', 'NORMAL')
            email = request.form.get('email', f"{username}@cardio.internal").strip()
            country_code = request.form.get('country_code', '+1').strip()
            local_phone = request.form.get('demo_phone', '').strip()
            if local_phone:
                if not local_phone.startswith('+') and country_code:
                    full_phone = PhoneService.format_phone(country_code, local_phone)
                else:
                    full_phone = local_phone
                is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
                demo_phone = validated_phone or full_phone
            else:
                demo_phone = '+1 (555) 019-2830'

            photo_file = request.files.get('profile_photo')
            photo_filename = None
            if photo_file and photo_file.filename:
                photo_filename, err = PhotoService.validate_and_save(photo_file, 'doctor')
                if err:
                    flash(f"Photo upload warning: {err}. Using default avatar.", "warning")

            if doctor_id and username and password and name:
                try:
                    user_uid = f"U_{doctor_id}"
                    execute_db('''
                        INSERT INTO users (user_id, username, password_hash, role, name, email, status)
                        VALUES (?, ?, ?, 'doctor', ?, ?, 'active')
                    ''', (user_uid, username, generate_password_hash(password), name, email))

                    execute_db('''
                        INSERT INTO doctors (
                            doctor_id, user_id, name, profile_photo, specialty, specialization,
                            qualification, experience, department, email, demo_phone,
                            permission_level, trusted_device_id, status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DEV-DOC01-TRUSTED', 'active')
                    ''', (
                        doctor_id, user_uid, name, photo_filename, specialization, specialization,
                        qualification, experience, department, email, demo_phone,
                        permission_level
                    ))

                    AuditService.log(
                        user_id=session['user_id'], role='admin', action='CREATE_DOCTOR',
                        ip_address=request.remote_addr or '127.0.0.1', device_status='TRUSTED',
                        risk_score=10, risk_level='LOW', result='SUCCESS',
                        details=f"Admin created doctor account {name} ({doctor_id})"
                    )
                    flash(f"Doctor account {name} ({doctor_id}) registered successfully.", "success")
                except Exception as e:
                    flash(f"Registration error: {str(e)}", "danger")

        elif action_type == 'edit_doctor':
            doctor_id = request.form.get('doctor_id')
            name = request.form.get('name', '').strip()
            specialization = request.form.get('specialization', '').strip()
            qualification = request.form.get('qualification', '').strip()
            experience = request.form.get('experience', '').strip()
            department = request.form.get('department', '').strip()
            email = request.form.get('email', '').strip()
            permission_level = request.form.get('permission_level', 'NORMAL')
            status = request.form.get('status', 'active')

            country_code = request.form.get('country_code', '+1').strip()
            local_phone = request.form.get('demo_phone', '').strip()
            if local_phone:
                if not local_phone.startswith('+') and country_code:
                    full_phone = PhoneService.format_phone(country_code, local_phone)
                else:
                    full_phone = local_phone
                is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
                demo_phone = validated_phone or full_phone
            else:
                demo_phone = '+1 (555) 019-2830'

            photo_file = request.files.get('profile_photo')
            photo_filename = None
            if photo_file and photo_file.filename:
                photo_filename, err = PhotoService.validate_and_save(photo_file, 'doctor')
                if err:
                    flash(f"Photo upload error: {err}", "warning")

            UserModel.update_doctor_profile(
                doctor_id=doctor_id, name=name, specialization=specialization,
                qualification=qualification, experience=experience, department=department,
                demo_phone=demo_phone, permission_level=permission_level, status=status,
                email=email, profile_photo=photo_filename
            )

            AuditService.log(
                user_id=session['user_id'], role='admin', action='DOCTOR_PROFILE_UPDATED',
                ip_address=request.remote_addr or '127.0.0.1', device_status='TRUSTED',
                risk_score=10, risk_level='LOW', result='SUCCESS',
                details=f"Admin updated clinician profile for Doctor {name} ({doctor_id})"
            )
            flash(f"Doctor {doctor_id} profile updated successfully.", "success")

        return redirect(url_for('admin.manage_users'))

    doctors = UserModel.get_all_doctors()
    annotated_docs = []
    for d in doctors:
        doc_dict = dict(d)
        assigned = PatientModel.get_assigned_to_doctor(d['doctor_id'])
        doc_dict['assigned_patients'] = assigned
        risk_row = query_db("SELECT current_score, risk_level FROM risk_scores WHERE user_id = ? ORDER BY id DESC LIMIT 1", (d['user_id'],), one=True)
        doc_dict['risk_score'] = risk_row['current_score'] if risk_row else 10
        doc_dict['risk_level'] = risk_row['risk_level'] if risk_row else 'LOW'
        annotated_docs.append(doc_dict)

    return render_template('user_management.html', user=user, doctors=annotated_docs)

@admin_bp.route('/admin/doctors/<doctor_id>/photo', methods=['POST'])
def upload_doctor_photo(doctor_id):
    photo_file = request.files.get('photo')
    if photo_file and photo_file.filename:
        filename, err = PhotoService.validate_and_save(photo_file, 'doctor')
        if err:
            flash(f"Photo upload error: {err}", "danger")
        else:
            execute_db("UPDATE doctors SET profile_photo = ? WHERE doctor_id = ?", (filename, doctor_id))
            AuditService.log(
                user_id=session['user_id'], role='admin', action='DOCTOR_PHOTO_UPDATED',
                ip_address=request.remote_addr or '127.0.0.1', device_status='TRUSTED',
                risk_score=10, risk_level='LOW', result='SUCCESS',
                details=f"Admin updated profile photo for Doctor {doctor_id} ({filename})"
            )
            flash(f"Profile photo for Doctor {doctor_id} updated successfully.", "success")
    else:
        flash("No photo file selected.", "warning")
    return redirect(request.referrer or url_for('admin.manage_users'))

@admin_bp.route('/admin/doctors/<doctor_id>/photo/remove', methods=['POST'])
def remove_doctor_photo(doctor_id):
    doc = UserModel.get_doctor_by_doctor_id(doctor_id)
    if doc and doc['profile_photo']:
        PhotoService.delete_photo(doc['profile_photo'], 'doctor')
        UserModel.remove_doctor_photo(doctor_id)
        AuditService.log(
            user_id=session['user_id'], role='admin', action='DOCTOR_PHOTO_REMOVED',
            ip_address=request.remote_addr or '127.0.0.1', device_status='TRUSTED',
            risk_score=10, risk_level='LOW', result='SUCCESS',
            details=f"Admin removed profile photo for Doctor {doctor_id}. Default avatar restored."
        )
        flash(f"Profile photo removed for Doctor {doctor_id}. Default avatar restored.", "info")
    return redirect(request.referrer or url_for('admin.manage_users'))

@admin_bp.route('/admin/doctors/<doctor_id>/toggle-status', methods=['POST'])
def toggle_doctor_status(doctor_id):
    doc = UserModel.get_doctor_by_doctor_id(doctor_id)
    if doc:
        new_status = 'disabled' if doc['status'] == 'active' else 'active'
        UserModel.set_doctor_status(doctor_id, new_status)
        flash(f"Doctor {doctor_id} account status changed to {new_status.upper()}.", "info")
    return redirect(request.referrer or url_for('admin.manage_users'))

# =========================================================================
# PATIENT MANAGEMENT ROUTES
# =========================================================================

@admin_bp.route('/admin/patients', methods=['GET', 'POST'])
def manage_patients():
    user = UserModel.get_by_user_id(session['user_id'])

    if request.method == 'POST':
        action_type = request.form.get('action_type')

        if action_type == 'create_patient':
            patient_id = request.form.get('patient_id', '').strip().upper()
            name = request.form.get('name', '').strip()
            age = int(request.form.get('age', 60))
            gender = request.form.get('gender', 'Male')
            blood_group = request.form.get('blood_group', 'O+')
            assigned_doctor_id = request.form.get('assigned_doctor_id', 'D001')
            heart_condition_category = request.form.get('heart_condition_category', 'Critical Heart Patient').strip()
            medical_history = request.form.get('medical_history', 'Synthetic cardiology medical history.').strip()
            ecg_report = request.form.get('ecg_report', 'DEMO-ECG: Baseline sinus rhythm with ST elevation.').strip()
            echo_report = request.form.get('echo_report', 'Echo: LVEF reduced, apical hypokinesis.').strip()
            blood_test_report = request.form.get('blood_test_report', 'Troponin-I elevated, BNP elevated.').strip()
            current_prescriptions = request.form.get('current_prescriptions', 'Aspirin 81mg daily, Metoprolol 25mg daily').strip()
            emergency_contact = request.form.get('emergency_contact', 'Emergency contact - Synthetic Tel 555-0100').strip()
            record_sensitivity_level = request.form.get('record_sensitivity_level', 'NORMAL')
            status = request.form.get('status', 'active')

            country_code = request.form.get('country_code', '+1').strip()
            local_phone = request.form.get('phone_number', '').strip()
            if local_phone:
                if not local_phone.startswith('+') and country_code:
                    full_phone = PhoneService.format_phone(country_code, local_phone)
                else:
                    full_phone = local_phone
                is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
                phone_number = validated_phone or full_phone
            else:
                phone_number = '+1 (555) 019-1001'

            photo_file = request.files.get('profile_photo')
            photo_filename = None
            if photo_file and photo_file.filename:
                photo_filename, err = PhotoService.validate_and_save(photo_file, 'patient')
                if err:
                    flash(f"Photo upload error: {err}", "warning")

            if patient_id and name:
                try:
                    PatientModel.create_patient(
                        patient_id=patient_id, name=name, age=age, blood_group=blood_group,
                        gender=gender, assigned_doctor_id=assigned_doctor_id,
                        heart_condition_category=heart_condition_category,
                        medical_history=medical_history, ecg_report=ecg_report, echo_report=echo_report,
                        blood_test_report=blood_test_report, current_prescriptions=current_prescriptions,
                        emergency_contact=emergency_contact, record_sensitivity_level=record_sensitivity_level,
                        profile_photo=photo_filename, status=status, phone_number=phone_number
                    )
                    AuditService.log(
                        user_id=session['user_id'], role='admin', action='CREATE_PATIENT',
                        patient_id=patient_id, ip_address=request.remote_addr or '127.0.0.1',
                        device_status='TRUSTED', risk_score=10, risk_level='LOW', result='SUCCESS',
                        details=f"Admin added synthetic demo patient {name} ({patient_id})"
                    )
                    flash(f"Demo Patient {name} ({patient_id}) created successfully.", "success")
                except Exception as e:
                    flash(f"Error adding patient: {str(e)}", "danger")

        elif action_type == 'edit_patient':
            patient_id = request.form.get('patient_id')
            name = request.form.get('name', '').strip()
            age = int(request.form.get('age', 60))
            gender = request.form.get('gender', 'Male')
            blood_group = request.form.get('blood_group', 'O+')
            assigned_doctor_id = request.form.get('assigned_doctor_id', 'D001')
            heart_condition_category = request.form.get('heart_condition_category', '').strip()
            medical_history = request.form.get('medical_history', '').strip()
            ecg_report = request.form.get('ecg_report', '').strip()
            echo_report = request.form.get('echo_report', '').strip()
            blood_test_report = request.form.get('blood_test_report', '').strip()
            current_prescriptions = request.form.get('current_prescriptions', '').strip()
            emergency_contact = request.form.get('emergency_contact', '').strip()
            record_sensitivity_level = request.form.get('record_sensitivity_level', 'NORMAL')
            status = request.form.get('status', 'active')

            country_code = request.form.get('country_code', '+1').strip()
            local_phone = request.form.get('phone_number', '').strip()
            if local_phone:
                if not local_phone.startswith('+') and country_code:
                    full_phone = PhoneService.format_phone(country_code, local_phone)
                else:
                    full_phone = local_phone
                is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
                phone_number = validated_phone or full_phone
            else:
                phone_number = None

            photo_file = request.files.get('profile_photo')
            photo_filename = None
            if photo_file and photo_file.filename:
                photo_filename, err = PhotoService.validate_and_save(photo_file, 'patient')
                if err:
                    flash(f"Photo upload error: {err}", "warning")

            PatientModel.update_patient(
                patient_id=patient_id, name=name, age=age, blood_group=blood_group, gender=gender,
                assigned_doctor_id=assigned_doctor_id, heart_condition_category=heart_condition_category,
                medical_history=medical_history, ecg_report=ecg_report, echo_report=echo_report,
                blood_test_report=blood_test_report, current_prescriptions=current_prescriptions,
                emergency_contact=emergency_contact, record_sensitivity_level=record_sensitivity_level,
                status=status, profile_photo=photo_filename, phone_number=phone_number
            )

            AuditService.log(
                user_id=session['user_id'], role='admin', action='PATIENT_PROFILE_UPDATED',
                patient_id=patient_id, ip_address=request.remote_addr or '127.0.0.1',
                device_status='TRUSTED', risk_score=10, risk_level='LOW', result='SUCCESS',
                details=f"Admin updated synthetic demo patient profile {name} ({patient_id})"
            )
            flash(f"Patient {patient_id} updated successfully.", "success")

        return redirect(url_for('admin.manage_patients'))

    patients = PatientModel.get_all()
    all_doctors = UserModel.get_all_doctors()
    return render_template('admin_patients.html', user=user, patients=patients, doctors=all_doctors)

@admin_bp.route('/admin/patients/<patient_id>/photo', methods=['POST'])
def upload_patient_photo(patient_id):
    photo_file = request.files.get('photo')
    if photo_file and photo_file.filename:
        filename, err = PhotoService.validate_and_save(photo_file, 'patient')
        if err:
            flash(f"Photo upload error: {err}", "danger")
        else:
            execute_db("UPDATE patients SET profile_photo = ?, last_updated = CURRENT_TIMESTAMP WHERE patient_id = ?", (filename, patient_id))
            AuditService.log(
                user_id=session['user_id'], role='admin', action='PATIENT_PHOTO_UPDATED',
                patient_id=patient_id, ip_address=request.remote_addr or '127.0.0.1',
                device_status='TRUSTED', risk_score=10, risk_level='LOW', result='SUCCESS',
                details=f"Admin updated profile photo for Patient {patient_id} ({filename})"
            )
            flash(f"Profile photo for Patient {patient_id} updated successfully.", "success")
    else:
        flash("No photo file selected.", "warning")
    return redirect(request.referrer or url_for('admin.manage_patients'))

@admin_bp.route('/admin/patients/<patient_id>/photo/remove', methods=['POST'])
def remove_patient_photo(patient_id):
    p = PatientModel.get_by_id(patient_id)
    if p and p.get('profile_photo'):
        PhotoService.delete_photo(p['profile_photo'], 'patient')
        PatientModel.remove_patient_photo(patient_id)
        AuditService.log(
            user_id=session['user_id'], role='admin', action='PATIENT_PHOTO_REMOVED',
            patient_id=patient_id, ip_address=request.remote_addr or '127.0.0.1',
            device_status='TRUSTED', risk_score=10, risk_level='LOW', result='SUCCESS',
            details=f"Admin removed profile photo for Patient {patient_id}. Default avatar restored."
        )
        flash(f"Profile photo removed for Patient {patient_id}. Default avatar restored.", "info")
    return redirect(request.referrer or url_for('admin.manage_patients'))

@admin_bp.route('/admin/patients/<patient_id>/toggle-status', methods=['POST'])
def toggle_patient_status(patient_id):
    p = PatientModel.get_by_id(patient_id)
    if p:
        new_status = 'disabled' if p.get('status') == 'active' else 'active'
        PatientModel.set_patient_status(patient_id, new_status)
        flash(f"Patient demo record {patient_id} status changed to {new_status.upper()}.", "info")
    return redirect(request.referrer or url_for('admin.manage_patients'))

@admin_bp.route('/admin/assignments', methods=['GET', 'POST'])
def manage_assignments():
    user = UserModel.get_by_user_id(session['user_id'])

    if request.method == 'POST':
        action_type = request.form.get('action_type')
        doctor_id = request.form.get('doctor_id')
        patient_id = request.form.get('patient_id')

        if action_type == 'assign':
            execute_db('''
                INSERT INTO doctor_patient_assignments (doctor_id, patient_id, status)
                VALUES (?, ?, 'ACTIVE')
                ON CONFLICT(doctor_id, patient_id) DO UPDATE SET status = 'ACTIVE'
            ''', (doctor_id, patient_id))
            flash(f"Patient {patient_id} assigned to Doctor {doctor_id}.", "success")
        elif action_type == 'unassign':
            execute_db('''
                DELETE FROM doctor_patient_assignments
                WHERE doctor_id = ? AND patient_id = ?
            ''', (doctor_id, patient_id))
            flash(f"Patient {patient_id} unassigned from Doctor {doctor_id}.", "info")

        return redirect(url_for('admin.manage_assignments'))

    all_doctors = UserModel.get_all_doctors()
    all_patients = PatientModel.get_all()
    assignments = query_db('''
        SELECT a.*, d.name as doctor_name, d.profile_photo as doctor_photo,
               p.name as patient_name, p.profile_photo as patient_photo,
               p.heart_condition_category, p.record_sensitivity_level
        FROM doctor_patient_assignments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN patients p ON a.patient_id = p.patient_id
        WHERE a.status = 'ACTIVE'
        ORDER BY a.doctor_id, a.patient_id
    ''')

    return render_template(
        'doctor_patient_assignment.html',
        user=user,
        doctors=all_doctors,
        patients=all_patients,
        assignments=assignments
    )
