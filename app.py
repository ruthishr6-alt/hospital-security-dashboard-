import os
import sys
from flask import Flask, redirect, url_for, session, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import close_db, init_db
from database.seed import seed
from routes.auth import auth_bp
from routes.doctor import doctor_bp
from routes.admin import admin_bp
from routes.patients import patients_bp
from routes.security import security_bp
from routes.decoy import decoy_bp
from routes.cardioshield import cardioshield_bp
from models.user import UserModel
from services.threat_detector import ThreatDetector
from services.photo_service import PhotoService
from services.phone_service import PhoneService
from services.ehr_service import EhrService

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'heart-cybersec-vault-key-2026-critical-cardiac-auth'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(decoy_bp)
    app.register_blueprint(cardioshield_bp)

    # Teardown database
    app.teardown_appcontext(close_db)

    # Template filters for clean hospital EHR rendering
    app.jinja_env.filters['format_vitals'] = EhrService.format_vitals
    app.jinja_env.filters['parse_medications'] = EhrService.parse_medications

    # Security Headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Global context processor
    @app.context_processor
    def inject_globals():
        current_u = None
        current_doc = None
        current_pat = None
        threat_level = 'LOW'
        threat_color = 'threat-low'

        if 'user_id' in session:
            current_u = UserModel.get_by_user_id(session['user_id'])
            if current_u and current_u['role'] == 'doctor':
                current_doc = UserModel.get_doctor_by_user_id(session['user_id'])
                if current_doc:
                    current_u = dict(current_u)
                    current_u['doctor_id'] = current_doc['doctor_id']
            elif current_u and current_u['role'] == 'patient':
                from models.patient import PatientModel
                current_pat = PatientModel.get_by_user_id(session['user_id'])
                if current_pat:
                    current_u = dict(current_u)
                    current_u['patient_id'] = current_pat['patient_id']

        try:
            summary = ThreatDetector.get_summary_stats()
            threat_level = summary['threat_level']
            threat_color = summary['threat_color']
        except Exception:
            pass

        return {
            'current_user': current_u,
            'current_doctor': current_doc,
            'current_patient': current_pat if 'current_pat' in locals() else None,
            'DISCLAIMER': "DEMO DATA – NOT REAL PATIENT INFORMATION. ACADEMIC CYBERSECURITY PROTOTYPE ONLY.",
            'SYSTEM_NAME': "Cyber Security & Privacy Protection System for Critical Heart Patient Records",
            'system_threat_level': threat_level,
            'system_threat_color': threat_color,
            'session_device_id': session.get('device_id', 'DEV-DOC01-TRUSTED'),
            'session_device_status': session.get('device_status', 'TRUSTED'),
            'session_risk_score': session.get('risk_score', 10),
            'session_risk_level': session.get('risk_level', 'LOW'),
            'doctor_photo': PhotoService.get_doctor_photo_url,
            'patient_photo': PhotoService.get_patient_photo_url,
            'mask_phone': PhoneService.mask_phone,
            'country_codes': PhoneService.get_supported_country_codes(),
            'split_country_code': PhoneService.split_country_code,
            'parse_medications': EhrService.parse_medications,
            'format_vitals': EhrService.format_vitals
        }

    # Root route
    @app.route('/')
    def index():
        if 'user_id' in session:
            if session.get('role') == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif session.get('role') == 'patient':
                return redirect(url_for('auth.profile'))
            return redirect(url_for('doctor.dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/home')
    def home():
        from database.db import query_db
        doctors = UserModel.get_all_doctors()
        for d in doctors:
            cnt = query_db("SELECT count(*) as c FROM doctor_patient_assignments WHERE doctor_id = ?", (d['doctor_id'],), one=True)
            d['patient_count'] = cnt['c'] if cnt else 0
        devices = UserModel.get_all_devices()
        return render_template('login.html', all_devices=devices, doctors=doctors)

    return app

# Check and auto-initialize DB if needed
db_path = os.path.join(BASE_DIR, 'database', 'database.db')
if not os.path.exists(db_path):
    print("Database not found. Initializing and seeding...")
    seed()

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"===============================================================")
    print(f" Cyber Security & Privacy Protection System for Heart Patients")
    print(f" Running at: http://127.0.0.1:{port}")
    print(f" Demo Accounts:")
    print(f" - Admin: admin_demo | AdminDemo#2026!")
    print(f" - Doctor 1: doctor_demo_01 | DoctorDemo#2026!")
    print(f" - Doctor 2: doctor_demo_02 | DoctorDemo#2026!")
    print(f"===============================================================")
    app.run(host='127.0.0.1', port=port, debug=True)
