from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.db import query_db, execute_db
from models.patient import Patient
from services.auth_service import AuthService
from services.risk_engine import RiskEngine
from services.threat_detector import ThreatDetector
from services.deception_service import DeceptionService
from services.audit_service import AuditService

admin_bp = Blueprint('admin', __name__)

def current_admin():
    if 'user_id' not in session:
        return None
    user = AuthService.get_user_by_id(session['user_id'])
    if not user or user.get('role') != 'admin':
        return None
    return user

@admin_bp.before_request
def check_admin_auth():
    if request.endpoint and 'static' not in request.endpoint:
        if 'user_id' not in session:
            flash("Administrator authentication required.", "warning")
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            # Privilege escalation attempt!
            user = AuthService.get_user_by_id(session.get('user_id'))
            risk_eval = RiskEngine.evaluate_request(
                user=user,
                request_obj=request,
                resource_name='ADMIN_SECURITY_ZONE'
            )
            ThreatDetector.process_threat(user, request, risk_eval, action_name='ADMIN_PRIVILEGE_ESCALATION')
            AuditService.log(
                action='ADMIN_ACCESS_DENIED',
                risk_result=risk_eval,
                user=user,
                request_obj=request,
                resource='ADMIN_SETTINGS',
                details=f"Non-admin user '{session.get('username')}' attempted accessing admin setting"
            )
            flash("⛔ Access Denied: Administrator security clearance required.", "danger")
            return redirect(url_for('doctor.dashboard'))

@admin_bp.route('/admin/dashboard')
def dashboard():
    admin = current_admin()
    
    # Calculate Risk
    risk_eval = RiskEngine.evaluate_request(user=admin, request_obj=request, resource_name='ADMIN_DASHBOARD')
    AuditService.log('VIEW_ADMIN_DASHBOARD', risk_eval, admin, request, resource='SEC_DASHBOARD', details='Administrator viewed executive security dashboard')

    # Card Metrics
    critical_patients_count = query_db("SELECT COUNT(*) as cnt FROM real_patients WHERE condition_severity = 'CRITICAL'", one=True)['cnt']
    total_doctors_count = query_db("SELECT COUNT(*) as cnt FROM users WHERE role = 'doctor'", one=True)['cnt']
    threat_stats = ThreatDetector.get_threat_summary()
    audit_summary = AuditService.get_audit_summary()
    decoy_stats = DeceptionService.get_decoy_stats()

    cards = {
        'critical_patients': critical_patients_count,
        'authorized_doctors': total_doctors_count,
        'suspicious_activities': threat_stats['total_events'],
        'blocked_attempts': audit_summary['blocked_count'],
        'active_decoy_sessions': decoy_stats['total_interactions'],
        'threat_level': threat_stats['system_level'],
        'threat_color': threat_stats['color_class']
    }

    # Recent Security Events
    recent_events = ThreatDetector.get_recent_threats(limit=5)
    recent_decoys = DeceptionService.get_decoy_sessions(limit=5)

    return render_template(
        'admin_dashboard.html',
        user=admin,
        cards=cards,
        recent_events=recent_events,
        recent_decoys=recent_decoys,
        risk_eval=risk_eval
    )

@admin_bp.route('/admin/doctors', methods=['GET', 'POST'])
def manage_doctors():
    admin = current_admin()
    
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()
        specialty = request.form.get('specialty', '').strip()
        department = request.form.get('department', '').strip()
        email = request.form.get('email', '').strip()

        if user_id and username and password and name:
            try:
                AuthService.create_doctor(user_id, username, password, name, specialty, department, email)
                AuditService.log(
                    action='CREATE_DOCTOR_ACCOUNT',
                    risk_result={'score': 10, 'level': 'LOW', 'response_mode': 'REAL_SERVED'},
                    user=admin,
                    request_obj=request,
                    resource='USER_MANAGEMENT',
                    details=f"Admin created doctor account '{user_id}' ({name})"
                )
                flash(f"Doctor account {name} created successfully.", "success")
            except Exception as e:
                flash(f"Error creating doctor: {str(e)}", "danger")
        else:
            flash("All mandatory fields must be provided.", "warning")

        return redirect(url_for('admin.manage_doctors'))

    doctors = AuthService.get_doctors()
    # Fetch patient assignments for each doctor
    doctor_list = []
    for doc in doctors:
        d = dict(doc)
        assigned = query_db('''
            SELECT p.patient_id, p.name, a.access_level
            FROM doctor_patient_assignments a
            JOIN real_patients p ON a.patient_id = p.patient_id
            WHERE a.doctor_user_id = ?
        ''', (doc['user_id'],))
        d['assigned_patients'] = assigned
        doctor_list.append(d)

    all_patients = Patient.get_all_real()

    return render_template(
        'user_management.html',
        user=admin,
        doctors=doctor_list,
        all_patients=all_patients
    )

@admin_bp.route('/admin/assign-patient', methods=['POST'])
def assign_patient():
    admin = current_admin()
    doctor_id = request.form.get('doctor_user_id')
    patient_id = request.form.get('patient_id')
    access_level = request.form.get('access_level', 'PRIMARY_CARE')

    if doctor_id and patient_id:
        try:
            execute_db('''
                INSERT OR REPLACE INTO doctor_patient_assignments (doctor_user_id, patient_id, access_level)
                VALUES (?, ?, ?)
            ''', (doctor_id, patient_id, access_level))

            AuditService.log(
                action='GRANT_PATIENT_ACCESS',
                risk_result={'score': 10, 'level': 'LOW', 'response_mode': 'REAL_SERVED'},
                user=admin,
                request_obj=request,
                patient_id=patient_id,
                resource='ACCESS_CONTROL_MATRIX',
                details=f"Admin assigned patient {patient_id} to Dr. {doctor_id} ({access_level})"
            )
            flash(f"Patient {patient_id} successfully assigned to {doctor_id}.", "success")
        except Exception as e:
            flash(f"Assignment error: {str(e)}", "danger")

    return redirect(url_for('admin.manage_doctors'))

@admin_bp.route('/admin/unassign-patient', methods=['POST'])
def unassign_patient():
    admin = current_admin()
    doctor_id = request.form.get('doctor_user_id')
    patient_id = request.form.get('patient_id')

    execute_db('''
        DELETE FROM doctor_patient_assignments
        WHERE doctor_user_id = ? AND patient_id = ?
    ''', (doctor_id, patient_id))

    AuditService.log(
        action='REVOKE_PATIENT_ACCESS',
        risk_result={'score': 10, 'level': 'LOW', 'response_mode': 'REAL_SERVED'},
        user=admin,
        request_obj=request,
        patient_id=patient_id,
        resource='ACCESS_CONTROL_MATRIX',
        details=f"Admin revoked access for Dr. {doctor_id} to patient {patient_id}"
    )
    flash(f"Access revoked for {doctor_id} to {patient_id}.", "info")
    return redirect(url_for('admin.manage_doctors'))
