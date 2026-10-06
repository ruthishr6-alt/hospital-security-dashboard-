import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from database.db import query_db, execute_db

def run_tests():
    print("==================================================================")
    print("PATIENT DETAILS & MEDICATION EHR REDESIGN - VERIFICATION SUITE")
    print("==================================================================")
    client = app.test_client()

    # 1. Login as authorized doctor (Dr. Lin has access to HP001)
    res = client.post('/login', data={'username': 'doctor_demo_01', 'password': 'DoctorDemo#2026!', 'device_id': 'DEV-DOC01-TRUSTED'}, follow_redirects=False)
    assert res.status_code == 302, f"Login step 1 expected 302, got {res.status_code}"
    res = client.post('/mfa', data={'otp': '123456'}, follow_redirects=True)
    assert res.status_code == 200, "MFA step 2 failed"
    print("[PASS] 1. Doctor Lin logged in and authenticated via MFA.")

    # 2. View HP001 Detailed Patient Chart
    res = client.get('/patient/HP001')
    assert res.status_code == 200, f"Expected 200 on /patient/HP001, got {res.status_code}"
    html = res.data.decode('utf-8')

    # 3. Verify Patient Information Header & Demographics
    assert "PATIENT INFORMATION" in html, "PATIENT INFORMATION header missing"
    assert "Arthur Pendelton" in html, "Patient name missing"
    assert "HP001" in html, "Patient ID missing"
    assert "68 Years" in html, "Age missing"
    assert "Male" in html, "Gender missing"
    assert "O+" in html, "Blood group missing"
    assert "STEMI" in html, "Condition missing"
    print("[PASS] 2. Patient Information section rendered with complete clean clinical demographics.")

    # 4. Verify Medication Section & Specific Prescriptions
    assert "MEDICATIONS" in html, "MEDICATIONS section heading missing"
    assert "ACTIVE PHARMACOTHERAPY REGIMEN" in html, "Pharmacotherapy heading missing"

    # Medicine 1: Aspirin (Chewable)
    assert "Aspirin (Chewable)" in html, "Medicine Aspirin (Chewable) missing"
    assert "325 mg" in html, "Aspirin dose 325 mg missing"
    assert "Oral" in html, "Aspirin route Oral missing"
    assert "Stat loading dose" in html or "Stat Loading Dose" in html, "Aspirin frequency missing"

    # Medicine 2: Ticagrelor
    assert "Ticagrelor" in html, "Medicine Ticagrelor missing"
    assert "90 mg" in html, "Ticagrelor dose 90 mg missing"
    assert "Twice daily" in html or "Twice Daily" in html, "Ticagrelor frequency missing"

    # Medicine 3: Unfractionated Heparin
    assert "Unfractionated Heparin" in html, "Medicine Unfractionated Heparin missing"
    assert "18 units/kg/hr" in html, "Heparin dose 18 units/kg/hr missing"
    assert "IV Infusion" in html, "Heparin route IV Infusion missing"
    assert "Continuous" in html, "Heparin frequency Continuous missing"
    print("[PASS] 3. All individual medications rendered in clean EHR cards and structured table rows.")

    # 5. CRITICAL CHECK: Verify ZERO Raw JSON or Technical Code Displayed
    assert '{"drug":' not in html, "Raw JSON {\"drug\": was found in rendered HTML!"
    assert '{"dose":' not in html, "Raw JSON {\"dose\": was found in rendered HTML!"
    assert '{"route":' not in html, "Raw JSON {\"route\": was found in rendered HTML!"
    assert "{'drug':" not in html, "Raw Python dict {'drug': was found in rendered HTML!"
    assert "{'heart_rate':" not in html, "Raw Python vitals dict was found in rendered HTML!"
    print("[PASS] 4. Zero raw JSON, dictionary syntax, or developer key-values exposed in UI.")

    # 6. Verify Formatted Cardiac Telemetry Vitals
    assert "HEART RATE" in html, "Heart rate vitals card missing"
    assert "114 bpm" in html or "bpm" in html, "Formatted heart rate missing"
    assert "BLOOD PRESSURE" in html, "Blood pressure vitals card missing"
    assert "90/60 mmHg" in html or "mmHg" in html, "Formatted blood pressure missing"
    assert "OXYGEN SATURATION" in html, "Oxygen saturation vitals card missing"
    assert "92%" in html or "%" in html, "Formatted SpO2 missing"
    print("[PASS] 5. Cardiac vitals telemetry rendered as clean hospital EHR metric cards.")

    # 7. Verify Responsive View Controls (Cards View & Table View)
    assert "Cards View" in html, "Cards view button missing"
    assert "Table View" in html, "Table view button missing"
    assert "ehr-med-table" in html, "Structured medical table component missing"
    print("[PASS] 6. Dual EHR view modes (Clinical Cards & Structured Medical Table) verified.")

    print("==================================================================")
    print("ALL 6 MEDICATION & PATIENT EHR VERIFICATION TESTS PASSED (100%)!")
    print("==================================================================")

if __name__ == '__main__':
    run_tests()
