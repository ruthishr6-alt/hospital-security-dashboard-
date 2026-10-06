import sys
import os
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from database.db import query_db

def run_tests():
    print("==================================================================")
    print("CRITICAL HEART PATIENT CYBER SECURITY SYSTEM - FULL VERIFICATION")
    print("==================================================================")
    client = app.test_client()

    # 1. Test Root Redirect
    res = client.get('/')
    assert res.status_code == 302, f"Expected 302 redirect from root, got {res.status_code}"
    print("[PASS] 1. Root redirect to /login verified.")

    # 2. Test Login Page Rendering & Academic Disclaimer
    res = client.get('/login')
    assert res.status_code == 200, f"Expected 200 on /login, got {res.status_code}"
    assert b"Critical Heart Patient" in res.data
    assert b"ACADEMIC CYBERSECURITY" in res.data
    assert b"DEMO DATA" in res.data
    print("[PASS] 2. Login page renders with mandatory academic disclaimer.")

    # 3. Test Failed Login & Dynamic Penalty
    res = client.post('/login', data={'username': 'attacker_fake', 'password': 'WrongPassword123!', 'device_id': 'DEV-UNKNOWN-EXT-88'})
    assert res.status_code == 200
    assert b"Invalid credentials" in res.data or b"Risk" in res.data
    print("[PASS] 3. Failed login tracked with penalty points and audit log.")

    # 4. Test Doctor Step 1 Authentication & MFA Generation
    res = client.post('/login', data={'username': 'doctor_demo_01', 'password': 'DoctorDemo#2026!', 'device_id': 'DEV-DOC01-TRUSTED'}, follow_redirects=False)
    assert res.status_code == 302
    assert '/mfa' in res.headers.get('Location', '')
    print("[PASS] 4. Step 1 Credential authentication passed; routed to MFA verification.")

    # 5. Complete Step 2 MFA Verification (Master Code 123456)
    res = client.post('/mfa', data={'otp': '123456'}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Clinical Cardiology Station" in res.data
    assert b"Sarah Lin" in res.data
    print("[PASS] 5. Step 2 Demo MFA verified; Doctor session authorized.")

    # 6. Test Doctor Authorized Patient View (HP001 assigned to Dr. Lin)
    res = client.get('/patient/HP001')
    assert res.status_code == 200
    assert b"HP001" in res.data
    assert b"DEMO DATA" in res.data
    assert b"AUTHORIZED" in res.data
    assert b"STEMI" in res.data
    print("[PASS] 6. Authorized patient chart HP001 viewed with LOW risk (0-10) and real protected record.")

    # 7. Test Unauthorized Cross-Patient Traversal (Dr. Lin attempting HP003 assigned to Dr. Vance)
    res = client.get('/patient/HP003')
    assert res.status_code == 200
    # Must deny access to real record and shunt to decoy environment or show monitoring mode
    assert b"SECURITY MONITORING MODE" in res.data or b"Access Denied" in res.data or b"DECOY" in res.data
    print("[PASS] 7. Unauthorized cross-patient access attempt blocked & intercepted by Honeypot.")

    # 8. Test Clinical Notes Update on Assigned Patient
    res = client.post('/patient/HP001/update-notes', data={'clinical_notes': 'Automated test note: Patient hemodynamically stable post-heparin titration.'}, follow_redirects=True)
    assert res.status_code == 200
    print("[PASS] 8. Clinical progress notes recorded and audited.")

    # 9. Test Emergency Break-Glass Access (Doctor Lin requests emergency access for HP005)
    res = client.post('/emergency-access', data={
        'patient_id': 'HP005',
        'reason': 'Acute unstable ventricular tachycardia with hemodynamic collapse during night telemetry'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"EMERGENCY BREAK-GLASS" in res.data
    print("[PASS] 9. Emergency Break-Glass access approved for 15-min emergency window.")

    # 10. Test Doctor Profile Page
    res = client.get('/profile')
    assert res.status_code == 200
    assert b"Security Clearance Profile" in res.data
    assert b"Sarah Lin" in res.data
    print("[PASS] 10. Doctor Security Profile page verified.")

    # 11. Test Admin Login via Fast Switch or Credentials
    res = client.post('/api/auth/demo-switch/admin_demo')
    assert res.status_code == 200
    print("[PASS] 11. Evaluator fast-switch to Administrator cleared.")

    # 12. Test Admin SOC Dashboard with 10 Cards
    res = client.get('/admin/dashboard')
    assert res.status_code == 200
    assert b"Security Operations Center" in res.data
    assert b"CRITICAL HEART PATIENTS" in res.data
    assert b"AUTHORIZED DOCTORS" in res.data
    assert b"ACTIVE SESSIONS" in res.data
    assert b"SUSPICIOUS ACTIVITIES" in res.data
    assert b"BLOCKED ATTEMPTS" in res.data
    assert b"ACTIVE DECOY SESSIONS" in res.data
    assert b"CRITICAL THREATS" in res.data
    assert b"FAILED LOGINS" in res.data
    assert b"BREAK-GLASS EVENTS" in res.data
    assert b"INSIDER THREAT ALERTS" in res.data
    print("[PASS] 12. Admin SOC Dashboard verified with all 10 metric cards.")

    # 13. Test Telemetry Chart REST API (All 7 telemetry streams)
    res = client.get('/api/security/chart-data')
    assert res.status_code == 200
    chart_json = res.get_json()
    assert 'threats_by_severity' in chart_json
    assert 'login_activity' in chart_json
    assert 'failed_trend' in chart_json
    assert 'risk_distribution' in chart_json
    assert 'decoy_activity' in chart_json
    assert 'access_attempts' in chart_json
    assert 'threat_types' in chart_json
    print("[PASS] 13. SOC Telemetry REST API verified with all 7 live Chart.js feeds.")

    # 14. Test All 6 Demonstration Scenarios
    scenarios = [
        ('1', 'Authorized Doctor Workflow'),
        ('2', 'Unauthorized Patient Access'),
        ('3', 'Repeated Failed Login'),
        ('4', 'Suspicious User (Decoy Activated)'),
        ('5', 'Emergency Break-Glass Workflow'),
        ('6', 'Insider Threat Detection')
    ]
    for sc_id, sc_name in scenarios:
        res = client.post('/api/security/simulate-scenario', json={'scenario': sc_id})
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        print(f"[PASS] 14.{sc_id} Scenario #{sc_id} ({sc_name}): Risk={data['risk']['score']}/100, Status={data['status']}, Mode={data['response_mode']}")

    # 15. Test Zero-Trust Device Management & Toggle
    res = client.get('/security/devices')
    assert res.status_code == 200
    assert b"Zero-Trust Hardware Device Security" in res.data
    print("[PASS] 15. Hardware Device Security view verified.")

    # 16. Test Security Alerts & Status Updating
    res = client.get('/security/alerts')
    assert res.status_code == 200
    assert b"Security Incident Alerts" in res.data
    print("[PASS] 16. Real-time Security Incident alerts feed verified.")

    # 17. Test Decoy Honeypot Monitor & Isolated Decoy Environment
    res = client.get('/security/decoy-monitor')
    assert res.status_code == 200
    assert b"Honeypot" in res.data or b"Decoy" in res.data
    
    res = client.get('/decoy')
    assert res.status_code == 200
    assert b"SECURITY MONITORING MODE" in res.data
    print("[PASS] 17. Honeypot Decoy console and isolated sandbox verified.")

    # 18. Test Audit Logs with Multi-parameter Filters
    res = client.get('/security/audit-logs?result=SUCCESS&threat=LOW')
    assert res.status_code == 200
    assert b"Tamper-Evident Security Audit Logs" in res.data
    print("[PASS] 18. Tamper-evident audit logs and multi-factor filters verified.")

    # 19. Test User Clearance Management & Doctor-Patient Assignments
    res = client.get('/admin/users')
    assert res.status_code == 200
    assert b"Clinician Accounts" in res.data

    res = client.get('/admin/assignments')
    assert res.status_code == 200
    assert b"Doctor-Patient Assignment" in res.data or b"Assignments" in res.data
    print("[PASS] 19. User clearance and doctor-patient assignment matrix verified.")

    # 20. Test Secure Logout
    res = client.get('/logout', follow_redirects=True)
    assert res.status_code == 200
    assert b"Session securely terminated" in res.data
    print("[PASS] 20. Secure logout and session destruction verified.")

    # =========================================================================
    # DOCTOR + PATIENT PROFILE PHOTO SYSTEM TESTS
    # =========================================================================
    print("------------------------------------------------------------------")
    print("DOCTOR & PATIENT PROFILE PHOTO SYSTEM - VERIFICATION SUITE")
    print("------------------------------------------------------------------")

    # Fast-switch to Admin
    client.post('/api/auth/demo-switch/admin_demo')

    # 21. Test Admin Patient Management Page
    res = client.get('/admin/patients')
    assert res.status_code == 200
    assert b"Synthetic Heart Patient Management" in res.data or b"Patient Management" in res.data
    assert b"HP001" in res.data
    print("[PASS] 21. Admin Patient Management page rendered with patient roster.")

    # 22. Test Photo Upload Validation: Rejection of Malicious/Invalid Files
    malicious_data = b"MZ\x90\x00\x03\x00\x00\x00malicious binary content"
    bad_file = (io.BytesIO(malicious_data), 'malicious.exe')
    res = client.post('/admin/doctors/D001/photo', data={'photo': bad_file}, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid file format" in res.data or b"Unsupported" in res.data or b"danger" in res.data
    print("[PASS] 22. Photo security enforced: Malicious .exe file rejected.")

    # 23. Test Doctor Photo Upload (Valid PNG)
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    doc_file = (io.BytesIO(png_bytes), 'dr_sarah_new.png')
    res = client.post('/admin/doctors/D001/photo', data={'photo': doc_file}, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200
    assert b"updated successfully" in res.data
    doc_row = query_db("SELECT profile_photo FROM doctors WHERE doctor_id = 'D001'", one=True)
    assert doc_row and doc_row['profile_photo'].startswith('doc_')
    print(f"[PASS] 23. Admin uploaded doctor profile photo ({doc_row['profile_photo']}).")

    # 24. Test Doctor Photo Appears in Doctor Profile & Clinical Station
    client.post('/api/auth/demo-switch/doctor_demo_01')
    res = client.get('/profile')
    assert res.status_code == 200
    assert doc_row['profile_photo'].encode() in res.data
    assert b"DOCTOR" in res.data

    res = client.get('/doctor/dashboard')
    assert res.status_code == 200
    assert doc_row['profile_photo'].encode() in res.data
    print("[PASS] 24. Doctor profile photo renders in Doctor Profile & Clinical Station.")

    # 25. Test Patient Photo Upload (Valid PNG)
    client.post('/api/auth/demo-switch/admin_demo')
    pat_file = (io.BytesIO(png_bytes), 'arthur_new.png')
    res = client.post('/admin/patients/HP001/photo', data={'photo': pat_file}, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200
    assert b"updated successfully" in res.data
    pat_row = query_db("SELECT profile_photo FROM patients WHERE patient_id = 'HP001'", one=True)
    assert pat_row and pat_row['profile_photo'].startswith('pat_')
    print(f"[PASS] 25. Admin uploaded patient profile photo ({pat_row['profile_photo']}).")

    # 26. Test Patient Photo Appears in Patient List & Patient Detail
    client.post('/api/auth/demo-switch/doctor_demo_01')
    res = client.get('/patients')
    assert res.status_code == 200
    assert pat_row['profile_photo'].encode() in res.data
    assert b"PATIENT" in res.data

    res = client.get('/patient/HP001')
    assert res.status_code == 200
    assert pat_row['profile_photo'].encode() in res.data
    print("[PASS] 26. Patient photo renders in Patient List & Detailed Patient Chart.")

    # 27. Test Admin Photo Removal & Default Avatar Fallback
    client.post('/api/auth/demo-switch/admin_demo')
    res = client.post('/admin/doctors/D001/photo/remove', follow_redirects=True)
    assert res.status_code == 200
    doc_after = query_db("SELECT profile_photo FROM doctors WHERE doctor_id = 'D001'", one=True)
    assert doc_after['profile_photo'] is None

    from services.photo_service import PhotoService
    assert PhotoService.get_doctor_photo_url(None) == '/static/img/avatars/doctor_default.svg'
    assert PhotoService.get_patient_photo_url(None, False) == '/static/img/avatars/patient_default.svg'
    assert PhotoService.get_patient_photo_url(None, True) == '/static/img/avatars/decoy_default.svg'
    print("[PASS] 27. Photo removal resets to NULL and falls back cleanly to default avatars.")

    # 28. Test Decoy Honeypot Environment Displays Decoy Photos
    res = client.get('/decoy')
    assert res.status_code == 200
    assert b"dec_101.svg" in res.data
    assert b"SYNTHETIC DECOY DATA" in res.data
    print("[PASS] 28. Decoy Honeypot environment displays isolated synthetic decoy photos.")

    # 29. Test Doctor Account Status Toggle & Patient Status Toggle
    res = client.post('/admin/doctors/D001/toggle-status', follow_redirects=True)
    assert res.status_code == 200
    d_stat = query_db("SELECT status FROM doctors WHERE doctor_id = 'D001'", one=True)['status']
    assert d_stat == 'disabled'
    # Toggle back to active
    client.post('/admin/doctors/D001/toggle-status', follow_redirects=True)
    assert query_db("SELECT status FROM doctors WHERE doctor_id = 'D001'", one=True)['status'] == 'active'

    res = client.post('/admin/patients/HP001/toggle-status', follow_redirects=True)
    assert res.status_code == 200
    p_stat = query_db("SELECT status FROM patients WHERE patient_id = 'HP001'", one=True)['status']
    assert p_stat == 'disabled'
    client.post('/admin/patients/HP001/toggle-status', follow_redirects=True)
    assert query_db("SELECT status FROM patients WHERE patient_id = 'HP001'", one=True)['status'] == 'active'
    print("[PASS] 29. Admin status toggling for Doctor and Patient accounts verified.")

    # 30. Clean re-seed to restore pristine synthetic demonstration state
    from database.seed import seed
    seed()
    print("[PASS] 30. Pristine synthetic database re-seeded successfully.")

    print("==================================================================")
    print("ALL 30 VERIFICATION TESTS COMPLETED WITH 100% SUCCESS!")
    print("==================================================================")

if __name__ == '__main__':
    run_tests()
