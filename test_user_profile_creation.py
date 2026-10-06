import os
import sys
import io
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from database.db import query_db, execute_db

def cleanup_test_users():
    """Removes temporary test accounts to ensure idempotent test runs."""
    try:
        users = query_db("SELECT user_id FROM users WHERE username LIKE '%_test%'")
        for u in users:
            uid = u['user_id']
            execute_db("DELETE FROM doctors WHERE user_id = ?", (uid,))
            execute_db("DELETE FROM patients WHERE user_id = ?", (uid,))
            execute_db("DELETE FROM device_status WHERE user_id = ?", (uid,))
            execute_db("DELETE FROM audit_logs WHERE user_id = ?", (uid,))
        execute_db("DELETE FROM users WHERE username LIKE '%_test%'")
    except Exception as e:
        print(f"Cleanup warning: {e}")

def run_tests():
    print("==================================================================")
    print("USER PROFILE CREATION & SELF-MANAGEMENT - VERIFICATION SUITE")
    print("==================================================================")
    cleanup_test_users()
    client = app.test_client()

    # ------------------------------------------------------------------
    # 1. Profile Creation Hub
    # ------------------------------------------------------------------
    res = client.get('/create-profile')
    assert res.status_code == 200, f"Expected 200 on /create-profile, got {res.status_code}"
    assert b"Create Your Healthcare Profile" in res.data, "Missing hub title"
    assert b"Doctor Profile" in res.data, "Missing Doctor Profile tab"
    assert b"Patient Profile" in res.data, "Missing Patient Profile tab"
    assert b"ACADEMIC CYBERSECURITY PROTOTYPE" in res.data, "Missing disclaimer"
    print("[PASS] 1. Registration hub /create-profile rendered with Doctor & Patient tabs.")

    # ------------------------------------------------------------------
    # 2. Doctor Registration with Auto-Generated ID
    # ------------------------------------------------------------------
    ts = int(time.time())
    doc_user = f"dr_priya_{ts}_test"
    doc_form = {
        'name': 'Dr. Priya Sharma',
        'specialization': 'Interventional Cardiology',
        'department': 'Cardiac Catheterization Lab',
        'qualification': 'MBBS, MD, DM Cardiology',
        'experience': '10 Years',
        'email': 'priya.sharma@hospital-secure.demo',
        'country_code': '+1',
        'demo_phone': '(555) 019-7788',
        'username': doc_user,
        'password': 'SecurePassword123!',
        'doctor_id': ''  # Test auto-generation
    }
    res = client.post('/register/doctor', data=doc_form, follow_redirects=True)
    assert res.status_code == 200, f"Expected 200 after doctor registration, got {res.status_code}"
    assert b"Clinician Profile &amp; Security Clearance" in res.data, "Should redirect to profile"
    assert b"Dr. Priya Sharma" in res.data, "Doctor name missing in profile"
    assert b"Interventional Cardiology" in res.data, "Specialization missing in profile"

    # Verify DB state
    db_u = query_db("SELECT * FROM users WHERE username = ?", (doc_user,), one=True)
    assert db_u is not None, "Doctor user not found in DB"
    assert db_u['role'] == 'doctor', "User role should be 'doctor'"

    db_doc = query_db("SELECT * FROM doctors WHERE user_id = ?", (db_u['user_id'],), one=True)
    assert db_doc is not None, "Doctor record not found in DB"
    assert db_doc['doctor_id'].startswith('DOC'), f"Auto-generated ID should start with DOC: {db_doc['doctor_id']}"

    db_audit = query_db("SELECT * FROM audit_logs WHERE action = 'DOCTOR_REGISTERED' AND user_id = ?", (db_u['user_id'],), one=True)
    assert db_audit is not None, "DOCTOR_REGISTERED audit log missing"
    print(f"[PASS] 2. Doctor registered with auto-generated ID ({db_doc['doctor_id']}) and authenticated.")

    # ------------------------------------------------------------------
    # 3. Doctor Self-Profile Update
    # ------------------------------------------------------------------
    doc_edit_form = {
        'name': 'Dr. Priya S. Sharma',
        'specialization': 'Advanced Pediatric Cardiology',
        'department': 'Pediatric Heart Center',
        'qualification': 'MBBS, MD, FACC',
        'experience': '12 Years',
        'email': 'priya.advanced@hospital-secure.demo',
        'country_code': '+44',
        'demo_phone': '7911 123456'
    }
    res = client.post('/profile/edit', data=doc_edit_form, follow_redirects=True)
    assert res.status_code == 200, f"Expected 200 after doctor edit, got {res.status_code}"
    assert b"Advanced Pediatric Cardiology" in res.data, "Updated specialization not rendered"
    assert b"Pediatric Heart Center" in res.data, "Updated department not rendered"

    audit_edit = query_db("SELECT * FROM audit_logs WHERE action = 'PROFILE_UPDATED' AND user_id = ? ORDER BY id DESC", (db_u['user_id'],), one=True)
    assert audit_edit is not None, "Doctor PROFILE_UPDATED audit log missing"
    print("[PASS] 3. Doctor self-profile editing verified and audit-logged.")

    # ------------------------------------------------------------------
    # 4. Patient Registration with Auto-Generated ID
    # ------------------------------------------------------------------
    pat_user = f"aarav_patel_{ts}_test"
    pat_form = {
        'name': 'Aarav Patel',
        'email': 'aarav.patel@demo-health.test',
        'country_code': '+91',
        'phone_number': '98765 43210',
        'age': '48',
        'gender': 'Male',
        'blood_group': 'B+',
        'patient_id': '',  # Test auto-generation
        'emergency_contact': 'Spouse: Sunita Patel - +91 98765 43211',
        'heart_condition_category': 'Coronary Artery Disease (CAD)',
        'medical_history': 'Prior angioplasty, mild hypertension managed with medication.',
        'assigned_doctor_id': 'DOC001',
        'username': pat_user,
        'password': 'PatientPassword123!'
    }
    res = client.post('/register/patient', data=pat_form, follow_redirects=True)
    assert res.status_code == 200, f"Expected 200 after patient registration, got {res.status_code}"
    assert b"Patient Health Profile &amp; Privacy Shield" in res.data, "Should redirect to patient profile"
    assert b"Aarav Patel" in res.data, "Patient name missing in profile"
    assert b"Coronary Artery Disease (CAD)" in res.data, "Condition missing in profile"
    assert b"Sunita Patel" in res.data, "Emergency contact missing in profile"

    # Verify DB state
    db_pu = query_db("SELECT * FROM users WHERE username = ?", (pat_user,), one=True)
    assert db_pu is not None, "Patient user not found in DB"
    assert db_pu['role'] == 'patient', "User role should be 'patient'"

    db_pat = query_db("SELECT * FROM patients WHERE user_id = ?", (db_pu['user_id'],), one=True)
    assert db_pat is not None, "Patient record not found in DB"
    assert db_pat['patient_id'].startswith('HP'), f"Auto-generated ID should start with HP: {db_pat['patient_id']}"

    db_paudit = query_db("SELECT * FROM audit_logs WHERE action = 'PATIENT_REGISTERED' AND user_id = ?", (db_pu['user_id'],), one=True)
    assert db_paudit is not None, "PATIENT_REGISTERED audit log missing"
    print(f"[PASS] 4. Patient registered with auto-generated ID ({db_pat['patient_id']}) and authenticated.")

    # ------------------------------------------------------------------
    # 5. Patient Self-Profile Update
    # ------------------------------------------------------------------
    pat_edit_form = {
        'name': 'Aarav K. Patel',
        'email': 'aarav.updated@demo-health.test',
        'country_code': '+91',
        'phone_number': '98765 99999',
        'age': '49',
        'gender': 'Male',
        'blood_group': 'B+',
        'emergency_contact': 'Brother: Vikram Patel - +91 98765 88888',
        'heart_condition_category': 'Ischemic Cardiomyopathy',
        'medical_history': 'Post-revascularization recovery, normal EF, stable rhythm.'
    }
    res = client.post('/profile/edit', data=pat_edit_form, follow_redirects=True)
    assert res.status_code == 200, f"Expected 200 after patient edit, got {res.status_code}"
    assert b"Aarav K. Patel" in res.data, "Updated name not rendered"
    assert b"Vikram Patel" in res.data, "Updated emergency contact not rendered"
    assert b"Ischemic Cardiomyopathy" in res.data, "Updated condition not rendered"

    audit_pedit = query_db("SELECT * FROM audit_logs WHERE action = 'PATIENT_PROFILE_UPDATED' AND patient_id = ? ORDER BY id DESC", (db_pat['patient_id'],), one=True)
    assert audit_pedit is not None, "PATIENT_PROFILE_UPDATED audit log missing"
    print("[PASS] 5. Patient self-profile editing verified and audit-logged.")

    # ------------------------------------------------------------------
    # 6. Patient Zero-Trust Access Control (Own Chart vs Other Patients)
    # ------------------------------------------------------------------
    # 6a. Access own chart -> Authorized
    res_own = client.get(f"/patient/{db_pat['patient_id']}")
    assert res_own.status_code == 200, f"Expected 200 on own chart, got {res_own.status_code}"
    assert b"Aarav K. Patel" in res_own.data, "Own chart details not displayed"
    assert b"RESTRICTED ACCESS (SECURITY MONITORING MODE)" not in res_own.data, "Own chart should not trigger decoy"

    # 6b. Probe another patient's record (HP001) -> Blocked and diverted to Decoy
    res_other = client.get('/patient/HP001')
    assert res_other.status_code == 200, f"Expected 200 (decoy honeypot), got {res_other.status_code}"
    assert b"RESTRICTED ACCESS" in res_other.data, "Cross-patient probe should be restricted to decoy"

    audit_probe = query_db("SELECT * FROM audit_logs WHERE action = 'UNAUTHORIZED_PATIENT_ACCESS' AND user_id = ? ORDER BY id DESC", (db_pu['user_id'],), one=True)
    assert audit_probe is not None, "UNAUTHORIZED_PATIENT_ACCESS audit log missing"
    print("[PASS] 6. Zero-trust isolation enforced: Patient views own chart; cross-patient probe diverted to Decoy.")

    # ------------------------------------------------------------------
    # 7. Photo Upload Security & Removal
    # ------------------------------------------------------------------
    # 7a. Non-image file rejected
    bad_file = (io.BytesIO(b"malicious php payload"), "shell.php")
    res_bad = client.post('/profile/photo', data={'photo': bad_file}, content_type='multipart/form-data', follow_redirects=True)
    assert b"Invalid file format" in res_bad.data, "Non-image file was not rejected"

    # 7b. Valid PNG image accepted
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    good_file = (io.BytesIO(png_bytes), "profile_avatar.png")
    res_good = client.post('/profile/photo', data={'photo': good_file}, content_type='multipart/form-data', follow_redirects=True)
    assert b"Profile photo updated successfully" in res_good.data, "Valid photo upload failed"

    # 7c. Photo removed -> Default avatar restored
    res_rem = client.post('/profile/photo/remove', follow_redirects=True)
    assert b"Default avatar restored" in res_rem.data, "Photo removal did not restore default avatar"
    print("[PASS] 7. Profile photo security: invalid format blocked, PNG uploaded, default avatar restored.")

    # ------------------------------------------------------------------
    # 8. Field Validation (Email format, short password, duplicate username)
    # ------------------------------------------------------------------
    # 8a. Invalid email
    bad_email_form = doc_form.copy()
    bad_email_form['username'] = f"doc_bad_email_{ts}"
    bad_email_form['email'] = "not-an-email"
    res_be = client.post('/register/doctor', data=bad_email_form, follow_redirects=True)
    assert b"Please provide a valid email address" in res_be.data, "Invalid email was not rejected"

    # 8b. Short password
    bad_pwd_form = doc_form.copy()
    bad_pwd_form['username'] = f"doc_short_pwd_{ts}"
    bad_pwd_form['password'] = "123"
    res_bp = client.post('/register/doctor', data=bad_pwd_form, follow_redirects=True)
    assert b"Password must be at least 6 characters long" in res_bp.data, "Short password was not rejected"

    # 8c. Duplicate username
    dup_form = doc_form.copy()
    dup_form['username'] = doc_user  # already created in step 2
    res_dup = client.post('/register/doctor', data=dup_form, follow_redirects=True)
    assert b"already in use" in res_dup.data, "Duplicate username was not rejected"
    print("[PASS] 8. Form validation verified: Invalid email rejected, short password blocked, duplicate username handled.")

    # Cleanup test accounts
    cleanup_test_users()
    print("==================================================================")
    print("ALL 8 USER PROFILE CREATION TESTS COMPLETED WITH 100% SUCCESS!")
    print("==================================================================")

if __name__ == '__main__':
    run_tests()
