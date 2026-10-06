import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash
from services.auth_service import AuthService
from services.risk_engine import RiskEngine
from services.audit_service import AuditService
from services.threat_detector import ThreatDetector
from models.user import UserModel
from models.patient import PatientModel
from database.db import query_db, execute_db
from services.photo_service import PhotoService
from services.phone_service import PhoneService

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

def is_valid_email(email):
    if not email:
        return False
    return bool(re.match(EMAIL_REGEX, email.strip()))

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        device_id = request.form.get('device_id', 'DEV-DOC01-TRUSTED')
        
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
        device_info = UserModel.get_device(device_id)
        device_status = device_info['device_status'] if device_info else 'UNKNOWN'

        auth_result, error = AuthService.verify_credentials(username, password, ip_address=ip_address)

        if error:
            # Failed Login
            risk = RiskEngine.calculate_risk(
                user=None,
                action='LOGIN_FAILED',
                session_context={'ip_address': ip_address, 'device_id': device_id, 'device_status': device_status}
            )
            AuditService.log(
                user_id=username or 'UNKNOWN',
                role='unauthenticated',
                action='LOGIN_FAILED',
                ip_address=ip_address,
                device_status=device_status,
                risk_score=risk['score'],
                risk_level=risk['level'],
                result='DENIED',
                threat_type='FAILED_AUTHENTICATION',
                details=f"Failed login attempt for username: {username} from {device_id}"
            )
            if risk['score'] >= 80:
                ThreatDetector.analyze_event(
                    user_id=username or 'UNKNOWN',
                    action='LOGIN_FAILED',
                    risk_score=risk['score'],
                    details=f"Brute force credential stuffing detected: {risk['score']}/100",
                    threat_type='Brute Force Credential Attack',
                    severity='CRITICAL'
                )

            doctors = UserModel.get_all_doctors()
            for d in doctors:
                cnt = query_db("SELECT count(*) as c FROM doctor_patient_assignments WHERE doctor_id = ?", (d['doctor_id'],), one=True)
                d['patient_count'] = cnt['c'] if cnt else 0
            flash(f"⚠️ {error}", "danger")
            return render_template('login.html', username=username, failed_risk=risk, all_devices=UserModel.get_all_devices(), doctors=doctors)

        # Step 1 Success: Save pending auth and redirect to MFA
        user = auth_result['user']
        demo_otp = auth_result['demo_otp']

        session['pending_user_id'] = user['user_id']
        session['pending_username'] = user['username']
        session['pending_role'] = user['role']
        session['pending_name'] = user['name']
        session['pending_device_id'] = device_id
        session['pending_device_status'] = device_status
        session['demo_otp'] = demo_otp

        flash(f"Step 1 verified! Please complete Demo MFA Verification.", "info")
        return redirect(url_for('auth.mfa'))

    doctors = UserModel.get_all_doctors()
    for d in doctors:
        cnt = query_db("SELECT count(*) as c FROM doctor_patient_assignments WHERE doctor_id = ?", (d['doctor_id'],), one=True)
        d['patient_count'] = cnt['c'] if cnt else 0
    devices = UserModel.get_all_devices()
    return render_template('login.html', all_devices=devices, doctors=doctors)

@auth_bp.route('/mfa', methods=['GET', 'POST'])
def mfa():
    if 'pending_user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session.get('pending_user_id')
    username = session.get('pending_username')
    role = session.get('pending_role')
    device_id = session.get('pending_device_id', 'DEV-UNKNOWN-EXT-88')
    device_status = session.get('pending_device_status', 'UNKNOWN')
    expected_otp = session.get('demo_otp', '123456')

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()

        if AuthService.verify_otp(entered_otp, expected_otp):
            # Login Fully Approved
            session.clear()
            session['user_id'] = user_id
            session['username'] = username
            session['role'] = role
            session['device_id'] = device_id
            session['device_status'] = device_status
            session['session_id'] = f"SESS-{user_id[:6]}-{device_id[-4:]}"

            user_obj = UserModel.get_by_user_id(user_id)
            session['name'] = user_obj['name'] if user_obj else username

            # Calculate Initial Session Risk
            risk = RiskEngine.calculate_risk(
                user=user_obj,
                action='LOGIN_SUCCESS',
                session_context={'ip_address': ip_address, 'device_id': device_id, 'device_status': device_status, 'session_id': session['session_id']}
            )
            session['risk_score'] = risk['score']
            session['risk_level'] = risk['level']

            AuditService.log(
                user_id=user_id,
                role=role,
                action='LOGIN_SUCCESS',
                ip_address=ip_address,
                device_status=device_status,
                risk_score=risk['score'],
                risk_level=risk['level'],
                result='SUCCESS',
                session_id=session['session_id'],
                details=f"User {username} successfully authenticated via Demo MFA. Risk: {risk['score']}/100"
            )
            AuthService.clear_failed_attempts(ip_address)

            flash(f"Welcome, {session['name']}. Session authenticated.", "success")
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'patient':
                return redirect(url_for('auth.profile'))
            return redirect(url_for('doctor.dashboard'))
        else:
            flash("❌ Invalid Demo OTP code entered. Please re-check the simulated token.", "danger")

    return render_template('mfa.html', username=username, demo_otp=expected_otp, device_id=device_id, device_status=device_status)

# =========================================================================
# PROFILE CREATION / REGISTRATION HUB
# =========================================================================

@auth_bp.route('/create-profile', methods=['GET'])
@auth_bp.route('/register', methods=['GET'])
def create_profile_hub():
    role = request.args.get('role', 'doctor').lower()
    doctors = UserModel.get_all_doctors()
    country_codes = PhoneService.get_supported_country_codes()
    return render_template(
        'create_profile.html',
        selected_role=role,
        doctors=doctors,
        country_codes=country_codes
    )

@auth_bp.route('/register/doctor', methods=['GET', 'POST'])
def create_doctor_profile():
    if request.method == 'GET':
        return redirect(url_for('auth.create_profile_hub', role='doctor'))

    name = request.form.get('name', '').strip()
    specialization = request.form.get('specialization', '').strip()
    qualification = request.form.get('qualification', 'MBBS, MD Cardiology').strip()
    experience = request.form.get('experience', '5 Years').strip()
    department = request.form.get('department', 'Cardiology').strip()
    email = request.form.get('email', '').strip()
    doctor_id = request.form.get('doctor_id', '').strip().upper()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    country_code = request.form.get('country_code', '+1').strip()
    local_phone = request.form.get('demo_phone', '').strip() or request.form.get('phone_number', '').strip()

    if not name or not username or not password or not specialization or not department:
        flash("Please fill in all required fields (Name, Specialization, Department, Username, Password).", "danger")
        return redirect(url_for('auth.create_profile_hub', role='doctor'))

    if len(password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect(url_for('auth.create_profile_hub', role='doctor'))

    if not is_valid_email(email):
        flash("Please provide a valid email address.", "danger")
        return redirect(url_for('auth.create_profile_hub', role='doctor'))

    if UserModel.get_by_username(username):
        flash(f"Username '{username}' is already in use. Please choose another.", "danger")
        return redirect(url_for('auth.create_profile_hub', role='doctor'))

    if local_phone:
        full_phone = PhoneService.format_phone(country_code, local_phone) if not local_phone.startswith('+') else local_phone
        is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
        if not is_valid:
            flash(f"Phone validation warning: {p_err}. Please check your phone format.", "warning")
        demo_phone = validated_phone or full_phone
    else:
        demo_phone = '+1 (555) 019-2830'

    if not doctor_id:
        doctor_id = UserModel.generate_unique_doctor_id()
    else:
        if query_db("SELECT id FROM doctors WHERE doctor_id = ?", (doctor_id,), one=True):
            flash(f"Doctor ID '{doctor_id}' is already registered. Generating a unique ID.", "warning")
            doctor_id = UserModel.generate_unique_doctor_id()

    photo_file = request.files.get('profile_photo')
    photo_filename = None
    if photo_file and photo_file.filename:
        photo_filename, err = PhotoService.validate_and_save(photo_file, 'doctor')
        if err:
            flash(f"Photo upload warning: {err}. A default doctor avatar will be used.", "warning")

    user_uid = f"U_{doctor_id}"
    try:
        execute_db('''
            INSERT INTO users (user_id, username, password_hash, role, name, email, status)
            VALUES (?, ?, ?, 'doctor', ?, ?, 'active')
        ''', (user_uid, username, generate_password_hash(password), name, email))

        device_id = f"DEV-{doctor_id}-TRUSTED"
        execute_db('''
            INSERT INTO doctors (
                doctor_id, user_id, name, profile_photo, specialty, specialization,
                qualification, experience, department, email, demo_phone,
                permission_level, trusted_device_id, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NORMAL', ?, 'active')
        ''', (
            doctor_id, user_uid, name, photo_filename, specialization, specialization,
            qualification, experience, department, email, demo_phone, device_id
        ))

        execute_db('''
            INSERT OR IGNORE INTO device_status (device_id, user_id, device_name, device_status, risk_contribution)
            VALUES (?, ?, ?, 'TRUSTED', -5)
        ''', (device_id, user_uid, f"Clinician Station - {name}"))

        AuditService.log(
            user_id=user_uid,
            role='doctor',
            action='DOCTOR_REGISTERED',
            ip_address=request.remote_addr or '127.0.0.1',
            device_status='TRUSTED',
            risk_score=10,
            risk_level='LOW',
            result='SUCCESS',
            details=f"New clinician {name} created Doctor profile ({doctor_id}) with specialization {specialization}"
        )

        session.clear()
        session['user_id'] = user_uid
        session['username'] = username
        session['role'] = 'doctor'
        session['name'] = name
        session['doctor_id'] = doctor_id
        session['device_id'] = device_id
        session['device_status'] = 'TRUSTED'
        session['session_id'] = f"SESS-{user_uid[:6]}-REG"
        session['risk_score'] = 10
        session['risk_level'] = 'LOW'

        flash(f"Welcome, Dr. {name}! Your Doctor profile ({doctor_id}) has been created successfully.", "success")
        return redirect(url_for('auth.profile'))
    except Exception as e:
        flash(f"Profile creation error: {str(e)}", "danger")
        return redirect(url_for('auth.create_profile_hub', role='doctor'))

@auth_bp.route('/register/patient', methods=['GET', 'POST'])
def create_patient_profile():
    if request.method == 'GET':
        return redirect(url_for('auth.create_profile_hub', role='patient'))

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    age_str = request.form.get('age', '50').strip()
    gender = request.form.get('gender', 'Male').strip()
    blood_group = request.form.get('blood_group', 'O+').strip()
    patient_id = request.form.get('patient_id', '').strip().upper()
    emergency_contact = request.form.get('emergency_contact', '').strip()
    heart_condition_category = request.form.get('heart_condition_category', '').strip()
    medical_history = request.form.get('medical_history', '').strip() or 'Synthetic cardiology medical history.'
    assigned_doctor_id = request.form.get('assigned_doctor_id', 'D001').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    country_code = request.form.get('country_code', '+1').strip()
    local_phone = request.form.get('phone_number', '').strip()

    if not name or not username or not password or not emergency_contact or not heart_condition_category:
        flash("Please fill in all required fields (Name, Emergency Contact, Heart Condition, Username, Password).", "danger")
        return redirect(url_for('auth.create_profile_hub', role='patient'))

    try:
        age = int(age_str)
        if age < 1 or age > 120:
            raise ValueError()
    except ValueError:
        flash("Please enter a valid age between 1 and 120.", "danger")
        return redirect(url_for('auth.create_profile_hub', role='patient'))

    if len(password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect(url_for('auth.create_profile_hub', role='patient'))

    if not is_valid_email(email):
        flash("Please provide a valid email address.", "danger")
        return redirect(url_for('auth.create_profile_hub', role='patient'))

    if UserModel.get_by_username(username):
        flash(f"Username '{username}' is already in use. Please choose another.", "danger")
        return redirect(url_for('auth.create_profile_hub', role='patient'))

    if local_phone:
        full_phone = PhoneService.format_phone(country_code, local_phone) if not local_phone.startswith('+') else local_phone
        is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
        if not is_valid:
            flash(f"Phone validation warning: {p_err}. Please check your phone format.", "warning")
        phone_number = validated_phone or full_phone
    else:
        phone_number = '+1 (555) 019-1001'

    if not patient_id:
        patient_id = PatientModel.generate_unique_patient_id()
    else:
        if query_db("SELECT id FROM patients WHERE patient_id = ?", (patient_id,), one=True):
            flash(f"Patient ID '{patient_id}' is already registered. Generating a unique ID.", "warning")
            patient_id = PatientModel.generate_unique_patient_id()

    photo_file = request.files.get('profile_photo')
    photo_filename = None
    if photo_file and photo_file.filename:
        photo_filename, err = PhotoService.validate_and_save(photo_file, 'patient')
        if err:
            flash(f"Photo upload warning: {err}. A default patient avatar will be used.", "warning")

    user_uid = f"U_{patient_id}"
    try:
        execute_db('''
            INSERT INTO users (user_id, username, password_hash, role, name, email, status)
            VALUES (?, ?, ?, 'patient', ?, ?, 'active')
        ''', (user_uid, username, generate_password_hash(password), name, email))

        device_id = f"DEV-{patient_id}-TRUSTED"
        execute_db('''
            INSERT OR IGNORE INTO device_status (device_id, user_id, device_name, device_status, risk_contribution)
            VALUES (?, ?, ?, 'TRUSTED', -5)
        ''', (device_id, user_uid, f"Patient Portal Terminal - {name}"))

        PatientModel.create_patient(
            patient_id=patient_id,
            name=name,
            age=age,
            blood_group=blood_group,
            gender=gender,
            assigned_doctor_id=assigned_doctor_id,
            heart_condition_category=heart_condition_category,
            medical_history=medical_history,
            ecg_report='DEMO-ECG: Baseline sinus telemetry monitored.',
            echo_report='Echo: LVEF within monitored parameters.',
            blood_test_report='Biomarkers monitored: Normal cardiac enzymes.',
            current_prescriptions='Aspirin 81 mg Oral Once Daily, Metoprolol 25 mg Oral Twice Daily',
            emergency_contact=emergency_contact,
            record_sensitivity_level='NORMAL',
            profile_photo=photo_filename,
            status='active',
            phone_number=phone_number,
            user_id=user_uid,
            email=email
        )

        AuditService.log(
            user_id=user_uid,
            role='patient',
            action='PATIENT_REGISTERED',
            patient_id=patient_id,
            ip_address=request.remote_addr or '127.0.0.1',
            device_status='TRUSTED',
            risk_score=10,
            risk_level='LOW',
            result='SUCCESS',
            details=f"New patient {name} created Patient profile ({patient_id}) with condition {heart_condition_category}"
        )

        session.clear()
        session['user_id'] = user_uid
        session['username'] = username
        session['role'] = 'patient'
        session['name'] = name
        session['patient_id'] = patient_id
        session['device_id'] = device_id
        session['device_status'] = 'TRUSTED'
        session['session_id'] = f"SESS-{user_uid[:6]}-REG"
        session['risk_score'] = 10
        session['risk_level'] = 'LOW'

        flash(f"Welcome, {name}! Your Patient profile ({patient_id}) has been created successfully.", "success")
        return redirect(url_for('auth.profile'))
    except Exception as e:
        flash(f"Profile creation error: {str(e)}", "danger")
        return redirect(url_for('auth.create_profile_hub', role='patient'))

# =========================================================================
# PROFILE VIEW & SELF-EDIT ROUTES
# =========================================================================

@auth_bp.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = UserModel.get_by_user_id(session['user_id'])
    doc = UserModel.get_doctor_by_user_id(session['user_id']) if session.get('role') == 'doctor' else None
    pat = PatientModel.get_by_user_id(session['user_id']) if session.get('role') == 'patient' else None

    assigned_patients = []
    if doc:
        assigned_patients = PatientModel.get_assigned_to_doctor(doc['doctor_id'])

    recent_activity = AuditService.get_logs(limit=8, user_filter=session['user_id'])
    return render_template(
        'profile.html',
        user=user,
        doctor=doc,
        patient=pat,
        assigned_patients=assigned_patients,
        recent_activity=recent_activity
    )

@auth_bp.route('/profile/edit', methods=['POST'])
def edit_own_profile():
    if 'user_id' not in session:
        flash("Authentication required to update profile.", "danger")
        return redirect(url_for('auth.login'))

    user_role = session.get('role')

    if user_role == 'doctor':
        doc = UserModel.get_doctor_by_user_id(session['user_id'])
        if not doc:
            flash("Doctor profile not found.", "danger")
            return redirect(url_for('auth.profile'))

        name = request.form.get('name', '').strip() or doc['name']
        specialization = request.form.get('specialization', '').strip() or doc['specialization']
        qualification = request.form.get('qualification', '').strip() or doc.get('qualification', 'MBBS, MD Cardiology')
        experience = request.form.get('experience', '').strip() or doc.get('experience', '5 Years')
        department = request.form.get('department', '').strip() or doc['department']
        email = request.form.get('email', '').strip() or doc.get('email', '')

        country_code = request.form.get('country_code', '+1').strip()
        local_phone = request.form.get('demo_phone', '').strip() or request.form.get('phone_number', '').strip()
        if local_phone:
            full_phone = PhoneService.format_phone(country_code, local_phone) if not local_phone.startswith('+') else local_phone
            is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
            if not is_valid:
                flash(f"Phone validation: {p_err}", "warning")
            demo_phone = validated_phone or full_phone
        else:
            demo_phone = doc.get('demo_phone', '+1 (555) 019-2834')

        photo_file = request.files.get('profile_photo')
        photo_filename = None
        if photo_file and photo_file.filename:
            photo_filename, err = PhotoService.validate_and_save(photo_file, 'doctor')
            if err:
                flash(f"Photo upload error: {err}", "danger")

        UserModel.update_own_doctor_profile(
            doctor_id=doc['doctor_id'],
            name=name,
            specialization=specialization,
            qualification=qualification,
            experience=experience,
            department=department,
            demo_phone=demo_phone,
            email=email,
            profile_photo=photo_filename
        )
        session['name'] = name

        AuditService.log(
            user_id=session['user_id'],
            role='doctor',
            action='PROFILE_UPDATED',
            ip_address=request.remote_addr or '127.0.0.1',
            device_status=session.get('device_status', 'TRUSTED'),
            risk_score=10,
            risk_level='LOW',
            result='SUCCESS',
            session_id=session.get('session_id'),
            details=f"Doctor {doc['doctor_id']} ({name}) updated profile information (contact & clinical credentials)."
        )

        flash("Your clinician profile has been updated successfully.", "success")
        return redirect(url_for('auth.profile'))

    elif user_role == 'patient':
        pat = PatientModel.get_by_user_id(session['user_id'])
        if not pat:
            flash("Patient profile not found.", "danger")
            return redirect(url_for('auth.profile'))

        if pat.get('user_id') != session['user_id']:
            AuditService.log(
                user_id=session['user_id'], role='patient', action='UNAUTHORIZED_PROFILE_EDIT',
                ip_address=request.remote_addr or '127.0.0.1', device_status='UNKNOWN',
                risk_score=85, risk_level='CRITICAL', result='DENIED',
                details="Attempted unauthorized modification of another patient's profile record."
            )
            flash("Security violation: You can only edit your own profile.", "danger")
            return redirect(url_for('auth.profile'))

        name = request.form.get('name', '').strip() or pat['name']
        email = request.form.get('email', '').strip() or pat.get('email', '')
        emergency_contact = request.form.get('emergency_contact', '').strip() or pat['emergency_contact']
        heart_condition_category = request.form.get('heart_condition_category', '').strip() or pat['heart_condition_category']
        medical_history = request.form.get('medical_history', '').strip() or pat['medical_history']
        gender = request.form.get('gender', pat['gender']).strip()
        blood_group = request.form.get('blood_group', pat['blood_group']).strip()

        age = pat['age']
        age_str = request.form.get('age', '').strip()
        if age_str:
            try:
                age_val = int(age_str)
                if 1 <= age_val <= 120:
                    age = age_val
            except ValueError:
                pass

        country_code = request.form.get('country_code', '+1').strip()
        local_phone = request.form.get('phone_number', '').strip() or request.form.get('demo_phone', '').strip()
        if local_phone:
            full_phone = PhoneService.format_phone(country_code, local_phone) if not local_phone.startswith('+') else local_phone
            is_valid, validated_phone, p_err = PhoneService.validate_phone(full_phone)
            if not is_valid:
                flash(f"Phone validation: {p_err}", "warning")
            phone_number = validated_phone or full_phone
        else:
            phone_number = pat.get('phone_number', '+1 (555) 019-1001')

        photo_file = request.files.get('profile_photo')
        photo_filename = None
        if photo_file and photo_file.filename:
            photo_filename, err = PhotoService.validate_and_save(photo_file, 'patient')
            if err:
                flash(f"Photo upload error: {err}", "danger")

        PatientModel.update_own_patient_profile(
            patient_id=pat['patient_id'],
            name=name,
            phone_number=phone_number,
            email=email,
            emergency_contact=emergency_contact,
            heart_condition_category=heart_condition_category,
            medical_history=medical_history,
            age=age,
            gender=gender,
            blood_group=blood_group,
            profile_photo=photo_filename
        )
        session['name'] = name

        AuditService.log(
            user_id=session['user_id'],
            role='patient',
            action='PATIENT_PROFILE_UPDATED',
            patient_id=pat['patient_id'],
            ip_address=request.remote_addr or '127.0.0.1',
            device_status='TRUSTED',
            risk_score=10,
            risk_level='LOW',
            result='SUCCESS',
            session_id=session.get('session_id'),
            details=f"Patient {pat['patient_id']} ({name}) updated personal profile details."
        )

        flash("Your patient profile has been updated successfully.", "success")
        return redirect(url_for('auth.profile'))

    flash("Role not authorized for profile updates.", "danger")
    return redirect(url_for('auth.profile'))

@auth_bp.route('/profile/photo', methods=['POST'])
def upload_own_photo():
    if 'user_id' not in session:
        flash("Authorization required.", "danger")
        return redirect(url_for('auth.login'))

    user_role = session.get('role')
    photo_file = request.files.get('photo')
    if not photo_file or not photo_file.filename:
        flash("No photo file selected.", "warning")
        return redirect(url_for('auth.profile'))

    if user_role == 'doctor':
        doc = UserModel.get_doctor_by_user_id(session['user_id'])
        if not doc:
            flash("Doctor profile not found.", "danger")
            return redirect(url_for('auth.profile'))
        filename, err = PhotoService.validate_and_save(photo_file, 'doctor')
        if err:
            flash(f"Photo upload error: {err}", "danger")
        else:
            execute_db("UPDATE doctors SET profile_photo = ? WHERE doctor_id = ?", (filename, doc['doctor_id']))
            AuditService.log(
                user_id=session['user_id'], role='doctor', action='PHOTO_UPLOADED',
                ip_address=request.remote_addr or '127.0.0.1', device_status='TRUSTED',
                risk_score=10, risk_level='LOW', result='SUCCESS', session_id=session.get('session_id'),
                details=f"Doctor {doc['doctor_id']} uploaded new profile photo {filename}"
            )
            flash("Profile photo updated successfully.", "success")
    elif user_role == 'patient':
        pat = PatientModel.get_by_user_id(session['user_id'])
        if not pat:
            flash("Patient profile not found.", "danger")
            return redirect(url_for('auth.profile'))
        filename, err = PhotoService.validate_and_save(photo_file, 'patient')
        if err:
            flash(f"Photo upload error: {err}", "danger")
        else:
            execute_db("UPDATE patients SET profile_photo = ? WHERE patient_id = ?", (filename, pat['patient_id']))
            AuditService.log(
                user_id=session['user_id'], role='patient', action='PHOTO_UPLOADED', patient_id=pat['patient_id'],
                ip_address=request.remote_addr or '127.0.0.1', device_status='TRUSTED',
                risk_score=10, risk_level='LOW', result='SUCCESS', session_id=session.get('session_id'),
                details=f"Patient {pat['patient_id']} uploaded new profile photo {filename}"
            )
            flash("Profile photo updated successfully.", "success")
    return redirect(url_for('auth.profile'))

@auth_bp.route('/profile/photo/remove', methods=['POST'])
def remove_own_photo():
    if 'user_id' not in session:
        flash("Authorization required.", "danger")
        return redirect(url_for('auth.login'))

    user_role = session.get('role')
    if user_role == 'doctor':
        doc = UserModel.get_doctor_by_user_id(session['user_id'])
        if doc and doc.get('profile_photo'):
            PhotoService.delete_photo(doc['profile_photo'], 'doctor')
            UserModel.remove_doctor_photo(doc['doctor_id'])
            AuditService.log(
                user_id=session['user_id'], role='doctor', action='PHOTO_REMOVED',
                ip_address=request.remote_addr or '127.0.0.1', device_status='TRUSTED',
                risk_score=10, risk_level='LOW', result='SUCCESS', session_id=session.get('session_id'),
                details=f"Doctor {doc['doctor_id']} removed profile photo. Restored default avatar."
            )
            flash("Profile photo removed. Default avatar restored.", "info")
    elif user_role == 'patient':
        pat = PatientModel.get_by_user_id(session['user_id'])
        if pat and pat.get('profile_photo'):
            PhotoService.delete_photo(pat['profile_photo'], 'patient')
            PatientModel.remove_patient_photo(pat['patient_id'])
            AuditService.log(
                user_id=session['user_id'], role='patient', action='PHOTO_REMOVED', patient_id=pat['patient_id'],
                ip_address=request.remote_addr or '127.0.0.1', device_status='TRUSTED',
                risk_score=10, risk_level='LOW', result='SUCCESS', session_id=session.get('session_id'),
                details=f"Patient {pat['patient_id']} removed profile photo. Restored default avatar."
            )
            flash("Profile photo removed. Default avatar restored.", "info")
    return redirect(url_for('auth.profile'))

@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        AuditService.log(
            user_id=session['user_id'],
            role=session.get('role', 'doctor'),
            action='LOGOUT',
            ip_address=request.remote_addr or '127.0.0.1',
            device_status=session.get('device_status', 'TRUSTED'),
            risk_score=session.get('risk_score', 10),
            risk_level=session.get('risk_level', 'LOW'),
            result='SUCCESS',
            session_id=session.get('session_id'),
            details=f"User {session.get('username')} logged out securely"
        )
    session.clear()
    flash("Session securely terminated.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/auth/demo-switch/<username>', methods=['POST'])
def demo_switch(username):
    """Fast switcher for evaluators."""
    user = UserModel.get_by_username(username)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    session.clear()
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['name'] = user['name']
    session['device_id'] = 'DEV-DOC01-TRUSTED' if user['role'] == 'doctor' else 'DEV-ADMIN-TRUSTED'
    session['device_status'] = 'TRUSTED'
    session['session_id'] = f"SESS-{user['user_id'][:6]}-SWITCH"
    session['risk_score'] = 10
    session['risk_level'] = 'LOW'

    target = url_for('admin.dashboard') if user['role'] == 'admin' else url_for('doctor.dashboard')
    return jsonify({'success': True, 'redirect_url': target})
