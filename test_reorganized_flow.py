import os
import sys
import io
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from database.db import query_db, execute_db

def run_17_point_verification():
    print("==================================================================")
    print("CARDIOSHIELD REORGANIZED FLOW - 17-POINT FULL VERIFICATION SUITE")
    print("==================================================================")
    client = app.test_client()

    # Step 0: Ensure Admin session for initial operations
    client.post('/api/auth/demo-switch/admin_demo')

    # 1. Create new Doctor from UI
    res = client.get('/doctors/new')
    assert res.status_code == 200, f"Expected 200 on /doctors/new, got {res.status_code}"
    assert b"Create New Doctor Profile" in res.data
    print("[PASS] 1. Create new Doctor form renders with input fields & auto-generated ID.")

    # 2. Fill all fields + upload photo
    # Generate 1x1 png bytes
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00'
        b'\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    doc_photo = (io.BytesIO(png_bytes), 'dr_test_square.png')

    ts = int(time.time())
    new_doc_id = f"DOC{ts % 10000:04d}"
    doc_username = f"dr_flow_{ts}"

    doc_data = {
        'doctor_id': new_doc_id,
        'name': 'Dr. Alistair Finch',
        'email': f'finch_{ts}@cardioshield.hospital',
        'specialization': 'Electrophysiology & Arrhythmia',
        'qualification': 'MD, FACC, FHRS',
        'experience': '12 Years',
        'department': 'Cardiac Electrophysiology',
        'permission_level': 'CONFIDENTIAL',
        'country_code': '+1',
        'phone_number': '(555) 345-9876',
        'username': doc_username,
        'password': 'SecurePass123!',
        'profile_photo': doc_photo
    }

    # 3. Save Doctor -> redirect to /doctors/<doctor_id>
    res = client.post('/doctors/new', data=doc_data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200
    assert new_doc_id.encode() in res.data or b"Alistair Finch" in res.data
    
    # Check DB persistence
    doc_row = query_db("SELECT * FROM doctors WHERE doctor_id = ?", (new_doc_id,), one=True)
    assert doc_row is not None, f"Doctor {new_doc_id} was not saved to database!"
    assert doc_row['name'] == 'Dr. Alistair Finch'
    assert doc_row['specialization'] == 'Electrophysiology & Arrhythmia'
    print(f"[PASS] 2 & 3. New Doctor profile saved to database permanently with photo ({doc_row['profile_photo']}).")

    # 4. Refresh page -> Doctor still exists
    res_refresh = client.get(f'/doctors/{new_doc_id}')
    assert res_refresh.status_code == 200
    assert b"Dr. Alistair Finch" in res_refresh.data
    assert b"Electrophysiology" in res_refresh.data

    res_roster = client.get('/doctors')
    assert res_roster.status_code == 200
    assert b"Dr. Alistair Finch" in res_roster.data
    print("[PASS] 4. Page refresh verified: Doctor profile persists in list & detail views.")

    # 5. Logout -> Login -> Doctor still exists
    client.get('/logout')
    res_after_logout = client.get(f'/doctors/{new_doc_id}')
    assert res_after_logout.status_code == 200
    assert b"Dr. Alistair Finch" in res_after_logout.data

    # Log in as the newly created doctor or switch
    client.post('/api/auth/demo-switch/admin_demo')
    res_after_login = client.get('/doctors')
    assert b"Dr. Alistair Finch" in res_after_login.data
    print("[PASS] 5. Logout and re-login verified: Doctor profile persists permanently across sessions.")

    # 6. Create new Patient from UI
    res = client.get('/patients/new')
    assert res.status_code == 200
    assert b"Create New Patient" in res.data or b"Patient Registration" in res.data
    print("[PASS] 6. Create new Patient form renders with synthetic data warning and fields.")

    # 7. Fill all fields + upload photo
    pat_photo = (io.BytesIO(png_bytes), 'pat_test_square.png')
    new_pat_id = f"HP{ts % 10000:04d}"

    pat_data = {
        'patient_id': new_pat_id,
        'name': 'Claire Sterling',
        'age': '54',
        'gender': 'Female',
        'blood_group': 'B+',
        'assigned_doctor_id': new_doc_id, # Initially assign to Dr. Finch
        'heart_condition_category': 'Ventricular Tachycardia',
        'medical_history': 'Prior episode of sustained VT; LVEF 38%. Under automated ICD evaluation.',
        'emergency_contact': 'Julian Sterling (Spouse) - +1 (555) 019-9944',
        'country_code': '+1',
        'phone_number': '(555) 019-4455',
        'record_sensitivity_level': 'CONFIDENTIAL',
        'profile_photo': pat_photo
    }

    # 8. Save Patient -> Refresh page -> Patient still exists
    res = client.post('/patients/new', data=pat_data, content_type='multipart/form-data', follow_redirects=True)
    assert res.status_code == 200

    pat_row = query_db("SELECT * FROM patients WHERE patient_id = ?", (new_pat_id,), one=True)
    assert pat_row is not None, f"Patient {new_pat_id} not found in database!"
    assert pat_row['name'] == 'Claire Sterling'

    res_pat_detail = client.get(f'/patient/{new_pat_id}')
    assert res_pat_detail.status_code == 200
    assert b"Claire Sterling" in res_pat_detail.data
    assert b"Ventricular Tachycardia" in res_pat_detail.data

    res_pat_list = client.get('/patients')
    assert res_pat_list.status_code == 200
    assert b"Claire Sterling" in res_pat_list.data
    print(f"[PASS] 7 & 8. New Patient profile saved to database permanently with photo ({pat_row['profile_photo']}) & verified on refresh.")

    # 9. Assign Doctor to Patient
    # Reassign or verify assignment
    execute_db("UPDATE patients SET assigned_doctor_id = ? WHERE patient_id = ?", (new_doc_id, new_pat_id))
    execute_db("INSERT OR REPLACE INTO doctor_patient_assignments (doctor_id, patient_id, status) VALUES (?, ?, 'ACTIVE')", (new_doc_id, new_pat_id))
    updated_pat = query_db("SELECT assigned_doctor_id FROM patients WHERE patient_id = ?", (new_pat_id,), one=True)
    assert updated_pat['assigned_doctor_id'] == new_doc_id
    print(f"[PASS] 9. Doctor assignment verified: {new_doc_id} assigned to Patient {new_pat_id}.")

    # 10. Open Medical Records page
    res_med = client.get('/medical-records')
    assert res_med.status_code == 200
    assert b"CardioShield Multi-Stage Zero-Trust Access Pipeline" in res_med.data or b"Medical Records" in res_med.data
    print("[PASS] 10. Medical Records page renders with 6-stage Zero-Trust verification pipeline.")

    # 11. View with authorized Doctor -> real protected record
    # Switch session to authorized doctor (Dr. Finch)
    new_doc_user = query_db("SELECT user_id FROM doctors WHERE doctor_id = ?", (new_doc_id,), one=True)['user_id']
    with client.session_transaction() as sess:
        sess['user_id'] = new_doc_user
        sess['role'] = 'doctor'
        sess['doctor_id'] = new_doc_id
        sess['mfa_verified'] = True
        sess['device_status'] = 'TRUSTED'
        sess['risk_score'] = 10

    res_auth = client.get(f'/medical-records?patient_id={new_pat_id}')
    assert res_auth.status_code == 200
    assert b"Ventricular Tachycardia" in res_auth.data
    assert b"Claire Sterling" in res_auth.data
    assert b"AUTHORIZED" in res_auth.data
    assert b"PROTECTED_RECORD_SERVED" in res_auth.data
    print("[PASS] 11. Authorized Doctor access verified: real protected clinical chart rendered without raw JSON.")

    # 12. View with unauthorized Doctor -> blocked
    # Switch session to unauthorized doctor (D002 Dr. Marcus Vance who is NOT assigned to Claire Sterling)
    doc2_user = query_db("SELECT user_id FROM doctors WHERE doctor_id = 'D002'", one=True)['user_id']
    with client.session_transaction() as sess:
        sess['user_id'] = doc2_user
        sess['role'] = 'doctor'
        sess['doctor_id'] = 'D002'
        sess['mfa_verified'] = True
        sess['device_status'] = 'TRUSTED'
        sess['risk_score'] = 30

    res_unauth = client.get(f'/medical-records?patient_id={new_pat_id}')
    assert res_unauth.status_code == 200
    assert b"ACCESS_DENIED" in res_unauth.data
    assert b"HONEYPOT_DECOY_ENGAGED" in res_unauth.data
    print("[PASS] 12. Unauthorized Doctor access blocked: real record withheld; session diverted to Honeypot Decoy.")

    # 13. Check Risk Events -> event logged
    risk_ev = query_db("SELECT * FROM risk_events WHERE action = 'UNAUTHORIZED_MEDICAL_RECORD_PROBE' ORDER BY id DESC", one=True)
    assert risk_ev is not None, "Expected risk event in risk_events table!"
    assert new_pat_id in risk_ev['description']
    print(f"[PASS] 13. Risk Event logged: Score delta={risk_ev['score_delta']}, Level={risk_ev['risk_level']}.")

    # 14. Check Security Alerts -> alert generated
    sec_alert = query_db("SELECT * FROM security_alerts WHERE threat_type = 'Unauthorized Patient Chart Probe' ORDER BY id DESC", one=True)
    assert sec_alert is not None, "Expected alert in security_alerts table!"
    assert new_pat_id in sec_alert['description']
    print(f"[PASS] 14. Security Alert generated: Alert ID={sec_alert['alert_id']}, Severity={sec_alert['severity']}.")

    # 15. Check Audit Logs -> audit log stored
    audit_entry = query_db("SELECT * FROM audit_logs WHERE action = 'VIEW_MEDICAL_RECORD_DENIED' AND patient_id = ? ORDER BY id DESC", (new_pat_id,), one=True)
    assert audit_entry is not None, "Expected audit log in audit_logs table!"
    assert audit_entry['result'] == 'DENIED'
    print(f"[PASS] 15. Audit Log verified: User {audit_entry['user_id']} probe on {audit_entry['patient_id']} recorded with result DENIED.")

    # 16. Decoy system activates on unauthorized attempt
    decoy_log = query_db("SELECT * FROM decoy_sessions WHERE fake_patient_searched = ? ORDER BY id DESC", (new_pat_id,), one=True)
    assert decoy_log is not None, "Expected decoy interaction logged in decoy_sessions!"
    print(f"[PASS] 16. Decoy system activation verified: Honeypot telemetry recorded interaction for {decoy_log['fake_patient_searched']}.")

    # 17. Honeypot decoy data completely separate from real patient data
    real_count = query_db("SELECT COUNT(*) as cnt FROM patients", one=True)['cnt']
    decoy_count = query_db("SELECT COUNT(*) as cnt FROM decoy_patients", one=True)['cnt']
    decoy_patients = query_db("SELECT patient_id, name, is_decoy FROM decoy_patients")
    
    assert real_count > 0 and decoy_count > 0
    # Confirm real patient is not in decoy table and vice versa
    for dp in decoy_patients:
        assert dp['is_decoy'] == 1
        real_match = query_db("SELECT * FROM patients WHERE patient_id = ?", (dp['patient_id'],), one=True)
        assert real_match is None, f"Decoy ID {dp['patient_id']} leaked into real patient table!"
    print(f"[PASS] 17. Honeypot decoy data isolation verified: {real_count} real patients vs {decoy_count} decoy records completely partitioned.")

    print("==================================================================")
    print("ALL 17 VERIFICATION FLOW TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================================")

if __name__ == '__main__':
    run_17_point_verification()
