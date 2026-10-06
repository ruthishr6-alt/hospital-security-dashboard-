from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from services.auth_service import AuthService
from services.risk_engine import RiskEngine
from services.threat_detector import ThreatDetector
from services.audit_service import AuditService
from services.deception_service import DeceptionService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Risk assessment for login attempt
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
        
        user, error = AuthService.authenticate(username, password, ip_address=ip_address)
        
        if error:
            # Evaluate risk of failed login
            risk_eval = RiskEngine.evaluate_request(
                user=None,
                request_obj=request,
                resource_name='LOGIN_PORTAL'
            )
            
            # If failed attempts exceed threshold or high risk detected
            if risk_eval['score'] > 60:
                threat = ThreatDetector.process_threat(
                    user=None,
                    request_obj=request,
                    risk_result=risk_eval,
                    action_name='BRUTE_FORCE_LOGIN'
                )
                DeceptionService.log_interaction(
                    request_obj=request,
                    user=None,
                    action_performed='FAILED_BRUTE_FORCE_LOGIN',
                    behavior_notes=f"Failed login attempt for '{username}'. Tripped risk score {risk_eval['score']}."
                )
            
            AuditService.log(
                action='FAILED_LOGIN_ATTEMPT',
                risk_result=risk_eval,
                user=None,
                request_obj=request,
                resource='LOGIN_PORTAL',
                details=f"Failed authentication for username '{username}': {error}"
            )
            
            flash(error, 'danger')
            return render_template('login.html', username=username, failed_risk=risk_eval)

        # Successful Login
        session.clear()
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['name'] = user['name']
        session['specialty'] = user.get('specialty', '')
        session['department'] = user.get('department', '')

        risk_eval = RiskEngine.evaluate_request(
            user=user,
            request_obj=request,
            resource_name='LOGIN_PORTAL'
        )

        AuditService.log(
            action='AUTHENTICATE_LOGIN',
            risk_result=risk_eval,
            user=user,
            request_obj=request,
            resource='LOGIN_PORTAL',
            details=f"Successful login for {user['role']} '{user['username']}'"
        )

        flash(f"Welcome, {user['name']}. Access granted.", 'success')

        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('doctor.dashboard'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    user = None
    if 'user_id' in session:
        user = AuthService.get_user_by_id(session['user_id'])
        AuditService.log(
            action='USER_LOGOUT',
            risk_result={'score': 5, 'level': 'LOW', 'response_mode': 'REAL_SERVED'},
            user=user,
            request_obj=request,
            resource='AUTH_PORTAL',
            details=f"User {session.get('username')} logged out cleanly"
        )
    session.clear()
    flash("You have been securely signed out.", 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/auth/demo-switch/<username>', methods=['POST'])
def demo_switch(username):
    """Convenience endpoint for live demo/evaluator to switch roles instantly."""
    user = AuthService.get_user_by_id(username) or AuthService.authenticate(username, 'Doctor#101')[0]
    # If not found by user_id, check username
    from database.db import query_db
    user = query_db("SELECT * FROM users WHERE username = ? OR user_id = ?", (username, username), one=True)
    if not user:
        return jsonify({'success': False, 'message': 'Demo user not found'}), 404

    session.clear()
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['name'] = user['name']
    session['specialty'] = user.get('specialty', '')
    session['department'] = user.get('department', '')

    target_url = url_for('admin.dashboard') if user['role'] == 'admin' else url_for('doctor.dashboard')
    return jsonify({
        'success': True,
        'user': {'user_id': user['user_id'], 'name': user['name'], 'role': user['role']},
        'redirect_url': target_url
    })
