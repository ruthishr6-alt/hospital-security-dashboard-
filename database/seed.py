import json
import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db, init_db, DB_PATH

def seed():
    """Populates complete synthetic demo data for all entities."""
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

    # Re-initialize schema cleanly
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear existing data safely
    cursor.execute("PRAGMA foreign_keys = OFF")
    tables = [
        'users', 'doctors', 'patients', 'doctor_patient_assignments',
        'medical_records', 'confidential_records', 'emergency_access',
        'sessions', 'risk_scores', 'risk_events', 'security_alerts',
        'audit_logs', 'decoy_patients', 'decoy_records', 'decoy_sessions',
        'device_status', 'failed_logins'
    ]
    for tbl in tables:
        cursor.execute(f"DELETE FROM {tbl}")
    cursor.execute("PRAGMA foreign_keys = ON")

    # =========================================================================
    # 1. DEVICES
    # =========================================================================
    devices = [
        ('DEV-DOC01-TRUSTED', 'U_DOC01', 'Hospital ICU Workstation #01', 'TRUSTED', -5),
        ('DEV-DOC02-TRUSTED', 'U_DOC02', 'CCU Station Terminal #02', 'TRUSTED', -5),
        ('DEV-DOC03-TRUSTED', 'U_DOC03', 'Ward Medical Tablet #03', 'TRUSTED', -5),
        ('DEV-DOC04-TRUSTED', 'U_DOC04', 'EP Laboratory Desktop #04', 'TRUSTED', -5),
        ('DEV-DOC05-TRUSTED', 'U_DOC05', 'Heart Failure ICU Station #05', 'TRUSTED', -5),
        ('DEV-DOC06-TRUSTED', 'U_DOC06', 'Cardiology Clinic Terminal #06', 'TRUSTED', -5),
        ('DEV-DOC07-TRUSTED', 'U_DOC07', 'Pediatric Cardiology Tablet #07', 'TRUSTED', -5),
        ('DEV-DOC08-TRUSTED', 'U_DOC08', 'Surgical CCU Workstation #08', 'TRUSTED', -5),
        ('DEV-ADMIN-TRUSTED', 'U_ADMIN01', 'SOC Security Console #01', 'TRUSTED', -5),
        ('DEV-UNKNOWN-EXT-88', None, 'External Unknown Laptop (198.51.100.42)', 'UNKNOWN', 20),
        ('DEV-UNKNOWN-EXT-99', None, 'Anonymous Tor Exit / Public Wi-Fi', 'UNKNOWN', 20)
    ]
    cursor.executemany('''
        INSERT INTO device_status (device_id, user_id, device_name, device_status, risk_contribution)
        VALUES (?, ?, ?, ?, ?)
    ''', devices)

    # =========================================================================
    # 2. USERS & DOCTORS
    # =========================================================================
    pw_admin = generate_password_hash('AdminDemo#2026!')
    pw_doctor = generate_password_hash('DoctorDemo#2026!')

    users = [
        ('U_ADMIN01', 'admin_demo', pw_admin, 'admin', 'Alex Hayes, CISSP', 'alex.hayes@heartsec.internal', 'active'),
        ('U_DOC01', 'doctor_demo_01', pw_doctor, 'doctor', 'Dr. Sarah Lin, MD', 'sarah.lin@cardio.internal', 'active'),
        ('U_DOC02', 'doctor_demo_02', pw_doctor, 'doctor', 'Dr. Marcus Vance, MD', 'marcus.vance@cardio.internal', 'active'),
        ('U_DOC03', 'doctor_demo_03', pw_doctor, 'doctor', 'Dr. Elena Rostova, MD', 'elena.rostova@cardio.internal', 'active'),
        ('U_DOC04', 'doctor_demo_04', pw_doctor, 'doctor', 'Dr. David Kim, MD', 'david.kim@cardio.internal', 'active'),
        ('U_DOC05', 'doctor_demo_05', pw_doctor, 'doctor', 'Dr. Aisha Patel, MD', 'aisha.patel@cardio.internal', 'active'),
        ('U_DOC06', 'doctor_demo_06', pw_doctor, 'doctor', 'Dr. Arun Kumar, MD', 'arun.kumar@cardio.internal', 'active'),
        ('U_DOC07', 'doctor_demo_07', pw_doctor, 'doctor', 'Dr. Maya Chen, MD', 'maya.chen@cardio.internal', 'active'),
        ('U_DOC08', 'doctor_demo_08', pw_doctor, 'doctor', 'Dr. James Thornton, MD', 'james.thornton@cardio.internal', 'active')
    ]
    cursor.executemany('''
        INSERT INTO users (user_id, username, password_hash, role, name, email, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', users)

    doctors = [
        ('D001', 'U_DOC01', 'Dr. Sarah Lin, MD', 'doc_sarah_lin.jpg', 'Senior Interventional Cardiology', 'Senior Interventional Cardiology', 'MBBS, MD Cardiology, FACC', '12 Years', 'Cardiology ICU', 'sarah.lin@cardio.internal', '+1 (555) 019-2831', 'HIGHLY_CONFIDENTIAL', 'DEV-DOC01-TRUSTED', 'active'),
        ('D002', 'U_DOC02', 'Dr. Marcus Vance, MD', 'doc_marcus_vance.jpg', 'Staff Cardiologist', 'Cardiologist', 'MBBS, MD Internal Medicine, DM Cardiology', '9 Years', 'Cardiac Care Unit (CCU)', 'marcus.vance@cardio.internal', '+1 (555) 019-2832', 'CONFIDENTIAL', 'DEV-DOC02-TRUSTED', 'active'),
        ('D003', 'U_DOC03', 'Dr. Elena Rostova, MD', 'doc_elena_rostova.jpg', 'Resident Cardiologist', 'Cardiology Resident', 'MBBS, MD Cardiology', '4 Years', 'General Cardiology Ward', 'elena.rostova@cardio.internal', '+1 (555) 019-2833', 'NORMAL', 'DEV-DOC03-TRUSTED', 'active'),
        ('D004', 'U_DOC04', 'Dr. David Kim, MD', 'doc_david_kim.jpg', 'Electrophysiologist', 'Cardiac Electrophysiology', 'MBBS, MD, FHRS', '10 Years', 'Arrhythmia Care Unit', 'david.kim@cardio.internal', '+1 (555) 019-2834', 'CONFIDENTIAL', 'DEV-DOC04-TRUSTED', 'active'),
        ('D005', 'U_DOC05', 'Dr. Aisha Patel, MD', 'doc_aisha_patel.jpg', 'Advanced Heart Failure & Transplant', 'Heart Failure Specialist', 'MBBS, MD Cardiology, FHFSA', '15 Years', 'Heart Failure ICU', 'aisha.patel@cardio.internal', '+1 (555) 019-2835', 'HIGHLY_CONFIDENTIAL', 'DEV-DOC05-TRUSTED', 'active'),
        ('D006', 'U_DOC06', 'Dr. Arun Kumar, MD', 'doc_arun_kumar.jpg', 'Cardiologist', 'Cardiologist', 'MBBS, MD', '8 Years Experience', 'Cardiology Department', 'arun.kumar@cardio.internal', '+1 (555) 019-2836', 'CONFIDENTIAL', 'DEV-DOC06-TRUSTED', 'active'),
        ('D007', 'U_DOC07', 'Dr. Maya Chen, MD', 'doc_maya_chen.jpg', 'Pediatric Cardiology', 'Pediatric Cardiologist', 'MBBS, MD, PhD', '11 Years Experience', 'Pediatric Cardiology Unit', 'maya.chen@cardio.internal', '+1 (555) 019-2837', 'CONFIDENTIAL', 'DEV-DOC07-TRUSTED', 'active'),
        ('D008', 'U_DOC08', 'Dr. James Thornton, MD', 'doc_james_thornton.jpg', 'Cardiothoracic Specialist', 'Cardiothoracic Surgeon', 'MBBS, MS, MCh', '16 Years Experience', 'Cardiology Department', 'james.thornton@cardio.internal', '+1 (555) 019-2838', 'HIGHLY_CONFIDENTIAL', 'DEV-DOC08-TRUSTED', 'active')
    ]
    cursor.executemany('''
        INSERT INTO doctors (
            doctor_id, user_id, name, profile_photo, specialty, specialization,
            qualification, experience, department, email, demo_phone,
            permission_level, trusted_device_id, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', doctors)

    # =========================================================================
    # 3. PROTECTED DEMO HEART PATIENTS (12 Cases with Sensitivity Levels)
    # =========================================================================
    patients = [
        (
            'HP001', 'Arthur Pendelton', 68, 'O+', 'Male', 'D001',
            'Acute Anterior STEMI with Cardiogenic Shock',
            'Synthetic: Prior hypertension, type 2 diabetes mellitus (12 yrs), coronary stent placed 2021.',
            'DEMO-ECG-001: Hyperacute T waves with 3.5mm ST elevations across leads V1-V4. Reciprocal depressions in II, III, aVF.',
            'Transthoracic Echo: Hypokinesis of anterior and apical left ventricular walls. LVEF severely reduced (28%).',
            'Hs-Troponin-I: 14.8 ng/mL (Critical High, Ref <0.04) | NT-proBNP: 4,850 pg/mL | K+: 4.1 mEq/L',
            json.dumps([
                {'drug': 'Aspirin (Chewable)', 'dose': '325 mg', 'route': 'Oral', 'frequency': 'Stat loading dose'},
                {'drug': 'Ticagrelor', 'dose': '90 mg', 'route': 'Oral', 'frequency': 'Twice daily'},
                {'drug': 'Unfractionated Heparin', 'dose': '18 units/kg/hr', 'route': 'IV Infusion', 'frequency': 'Continuous titration'}
            ]),
            'Emergency Contact: Martha Pendelton (Wife) - Synthetic Tel 555-0191',
            'NORMAL',
            json.dumps({'heart_rate': 114, 'blood_pressure': '90/60 mmHg', 'spo2': '92%', 'temp': '37.1 C', 'resp_rate': 24, 'rhythm': 'Sinus Tachycardia with STEMI'})
        ),
        (
            'HP002', 'Helena Rostova', 54, 'A-', 'Female', 'D001',
            'Sustained Monomorphic Ventricular Tachycardia (VT)',
            'Synthetic: Non-ischemic dilated cardiomyopathy diagnosed 2023. Prior ablation therapy for atrial flutter.',
            'DEMO-ECG-002: Wide QRS complexes (> 160ms) at 178 bpm. AV dissociation noted with fusion and capture beats.',
            'Echo: Global left ventricular hypokinesis, severe mitral regurgitation (Grade III/IV), LVEF 24%.',
            'Serum Mg2+: 1.4 mg/dL (Low, Ref 1.7-2.2) | Troponin-I: 0.85 ng/mL | ABG pH: 7.31 (Acidotic)',
            json.dumps([
                {'drug': 'Amiodarone', 'dose': '150 mg in D5W', 'route': 'IV Infusion', 'frequency': 'Stat over 10 min, then 1 mg/min'},
                {'drug': 'Magnesium Sulfate', 'dose': '2 g', 'route': 'IV Piggyback', 'frequency': 'Stat over 20 min'}
            ]),
            'Emergency Contact: Boris Rostov (Brother) - Synthetic Tel 555-0192',
            'CONFIDENTIAL',
            json.dumps({'heart_rate': 178, 'blood_pressure': '82/50 mmHg', 'spo2': '90%', 'temp': '36.8 C', 'resp_rate': 26, 'rhythm': 'Wide Complex Ventricular Tachycardia'})
        ),
        (
            'HP003', 'Marcus Thorne', 72, 'B+', 'Male', 'D002',
            'Acute Decompensated Heart Failure (Wet & Cold Profile)',
            'Synthetic: Ischemic cardiomyopathy s/p CABG (2018), chronic kidney disease Stage 3b.',
            'DEMO-ECG-003: Left bundle branch block (LBBB) with QRS width 150ms. Secondary repolarization ST-T abnormalities.',
            'Echo: Severely reduced LVEF 22%, restrictive filling pattern (E/A ratio > 2.0). Dilated IVC without collapse.',
            'NT-proBNP: 9,200 pg/mL (Critical High) | Serum Creatinine: 2.1 mg/dL | BUN: 48 mg/dL',
            json.dumps([
                {'drug': 'Furosemide', 'dose': '80 mg', 'route': 'IV Bolus', 'frequency': 'Twice daily'},
                {'drug': 'Empagliflozin', 'dose': '10 mg', 'route': 'Oral', 'frequency': 'Daily morning'}
            ]),
            'Emergency Contact: Clara Thorne (Daughter) - Synthetic Tel 555-0193',
            'NORMAL',
            json.dumps({'heart_rate': 98, 'blood_pressure': '105/65 mmHg', 'spo2': '91%', 'temp': '36.9 C', 'resp_rate': 22, 'rhythm': 'Sinus with Frequent PVCs'})
        ),
        (
            'HP004', 'Sophia Lindqvist', 42, 'O-', 'Female', 'D002',
            'Severe Peripartum Cardiomyopathy with Apical Thrombus',
            'Synthetic: 3 weeks postpartum, acute onset progressive orthopnea, nocturnal dyspnea, bilateral lower limb anasarca.',
            'DEMO-ECG-004: Sinus tachycardia, biatrial enlargement, non-specific lateral lead T-wave flattenings.',
            'Echo: LVEF 18%. Clear 1.8cm pedunculated apical thrombus. Spontaneous echo contrast in left ventricle.',
            'NT-proBNP: 7,600 pg/mL | D-Dimer: 1.8 mcg/mL | Cardiac Enzymes: 0.12 ng/mL',
            json.dumps([
                {'drug': 'Enoxaparin', 'dose': '1 mg/kg', 'route': 'SubQ', 'frequency': 'Every 12 hours'},
                {'drug': 'Bromocriptine', 'dose': '2.5 mg', 'route': 'Oral', 'frequency': 'Daily'},
                {'drug': 'Carvedilol', 'dose': '3.125 mg', 'route': 'Oral', 'frequency': 'Twice daily'}
            ]),
            'Emergency Contact: Henrik Lindqvist (Spouse) - Synthetic Tel 555-0194',
            'HIGHLY_CONFIDENTIAL',
            json.dumps({'heart_rate': 108, 'blood_pressure': '95/62 mmHg', 'spo2': '94%', 'temp': '37.0 C', 'resp_rate': 20, 'rhythm': 'Sinus Tachycardia'})
        ),
        (
            'HP005', 'Dmitri Volkov', 61, 'AB+', 'Male', 'D003',
            'Critical Aortic Stenosis with Syncope and Cardiogenic Shock',
            'Synthetic: Bicuspid aortic valve history, exertional angina, documented recurrent syncopal episodes.',
            'DEMO-ECG-005: Severe LVH by voltage criteria (Sokolow-Lyon index > 42mm). Deep asymmetric T-wave inversions in I, aVL, V5-V6.',
            'Echo: Aortic valve area 0.58 cm2, mean transvalvular gradient 52 mmHg, peak jet velocity 4.8 m/s. LVEF 30%.',
            'Troponin-I: 0.42 ng/mL | Serum Lactate: 2.6 mmol/L | CBC Hemoglobin: 12.4 g/dL',
            json.dumps([
                {'drug': 'Norepinephrine', 'dose': '0.05 mcg/kg/min', 'route': 'IV Infusion', 'frequency': 'Titrate for MAP > 65'},
                {'drug': 'Furosemide', 'dose': '40 mg', 'route': 'IV Push', 'frequency': 'Daily'}
            ]),
            'Emergency Contact: Anna Volkova (Daughter) - Synthetic Tel 555-0195',
            'NORMAL',
            json.dumps({'heart_rate': 92, 'blood_pressure': '84/55 mmHg', 'spo2': '93%', 'temp': '36.7 C', 'resp_rate': 22, 'rhythm': 'Sinus Rhythm with LV Strain'})
        ),
        (
            'HP006', 'Grace Chen', 79, 'O+', 'Female', 'D004',
            'Complete Atrioventricular Heart Block (Third-Degree AV Block)',
            'Synthetic: Degenerative conduction system disease (Lev-Lenègre disease), coronary artery disease.',
            'DEMO-ECG-006: Complete AV dissociation. P wave rate 84 bpm, ventricular escape rhythm 34 bpm with broad atypical complexes.',
            'Echo: Preserved LVEF 50%, mild aortic regurgitation, normal ventricular dimensions.',
            'K+: 4.3 mEq/L | TSH: 2.1 mIU/L | Digoxin Level: <0.3 ng/mL (Non-toxic)',
            json.dumps([
                {'drug': 'Isoproterenol Infusion', 'dose': '2 mcg/min', 'route': 'IV Continuous', 'frequency': 'Bridge to pacemaker'},
                {'drug': 'Atropine', 'dose': '1 mg', 'route': 'IV Push', 'frequency': 'Stat in transit'}
            ]),
            'Emergency Contact: Kevin Chen (Son) - Synthetic Tel 555-0196',
            'CONFIDENTIAL',
            json.dumps({'heart_rate': 34, 'blood_pressure': '78/48 mmHg', 'spo2': '92%', 'temp': '36.4 C', 'resp_rate': 18, 'rhythm': 'Complete Heart Block with Escape'})
        ),
        (
            'HP007', 'Liam O Connor', 58, 'A+', 'Male', 'D004',
            'Subacute Bacterial Endocarditis with Severe Mitral Valve Flail',
            'Synthetic: Rheumatic heart disease in childhood, dental extraction 4 weeks prior without antibiotic prophylaxis.',
            'DEMO-ECG-007: Sinus tachycardia with PR interval prolongation (240ms - First-degree AV block with suspect perivalvular extension).',
            'Transesophageal Echo: Oscillating 14mm vegetation on anterior mitral leaflet, flail leaflet segment, severe eccentric MR. LVEF 45%.',
            'Blood Cultures: Positive for Streptococcus viridans | CRP: 118 mg/L (Critical High) | ESR: 84 mm/hr',
            json.dumps([
                {'drug': 'Ampicillin-Sulbactam', 'dose': '3 g', 'route': 'IV Infusion', 'frequency': 'Every 6 hours'},
                {'drug': 'Gentamicin', 'dose': '1 mg/kg', 'route': 'IV Infusion', 'frequency': 'Every 8 hours with trough monitor'}
            ]),
            'Emergency Contact: Fiona O Connor (Sister) - Synthetic Tel 555-0197',
            'NORMAL',
            json.dumps({'heart_rate': 102, 'blood_pressure': '112/68 mmHg', 'spo2': '95%', 'temp': '38.6 C', 'resp_rate': 20, 'rhythm': 'Sinus Tachycardia with 1st Degree AVB'})
        ),
        (
            'HP008', 'Fatima Zahra', 36, 'B-', 'Female', 'D005',
            'Adult Congenital Tetralogy of Fallot with Severe RV Dysfunction',
            'Synthetic: Complete repair of TOF at age 4. Progressive fatigue and reduced exercise capacity over past 6 months.',
            'DEMO-ECG-008: Classic right bundle branch block (RBBB) pattern with QRS duration 164ms. Right axis deviation (+120 degrees).',
            'Cardiac MRI: Free pulmonary regurgitation (regurgitant fraction 48%), RV end-diastolic volume index 168 mL/m2. LVEF 48%.',
            'BNP Level: 340 pg/mL (Elevated) | Serum Electrolytes: Normal limits',
            json.dumps([
                {'drug': 'Spironolactone', 'dose': '25 mg', 'route': 'Oral', 'frequency': 'Once daily'},
                {'drug': 'Bisoprolol', 'dose': '2.5 mg', 'route': 'Oral', 'frequency': 'Once daily'}
            ]),
            'Emergency Contact: Tariq Zahra (Father) - Synthetic Tel 555-0198',
            'NORMAL',
            json.dumps({'heart_rate': 78, 'blood_pressure': '118/74 mmHg', 'spo2': '97%', 'temp': '36.6 C', 'resp_rate': 16, 'rhythm': 'Sinus Rhythm with RBBB'})
        ),
        (
            'HP009', 'Raymond Sterling', 66, 'O+', 'Male', 'D005',
            'Massive Acute Pulmonary Embolism with Severe RV Strain',
            'Synthetic: Recent orthopedic knee arthroplasty (10 days ago), prolonged immobility, sudden pleuritic chest pain and collapse.',
            'DEMO-ECG-009: Classic McGinn-White S1Q3T3 sign (Prominent S in I, Q in III, inverted T in III). T-wave inversions V1-V4.',
            'Echo: McConnell sign (RV free wall hypokinesis with preserved apical contractility), severe pulmonary hypertension (RVSP 64 mmHg). LVEF 38%.',
            'D-Dimer: 12.4 mcg/mL (Critical High) | Hs-Troponin-T: 0.98 ng/mL | Serum Lactate: 3.8 mmol/L',
            json.dumps([
                {'drug': 'Alteplase (rt-PA)', 'dose': '100 mg', 'route': 'IV Infusion', 'frequency': 'Over 2 hours emergency thrombolysis'},
                {'drug': 'Heparin Infusion', 'dose': '80 u/kg bolus, 18 u/kg/hr', 'route': 'IV Infusion', 'frequency': 'Post-lysis continuous titration'}
            ]),
            'Emergency Contact: Victoria Sterling (Wife) - Synthetic Tel 555-0199',
            'CONFIDENTIAL',
            json.dumps({'heart_rate': 128, 'blood_pressure': '86/56 mmHg', 'spo2': '88%', 'temp': '37.2 C', 'resp_rate': 32, 'rhythm': 'Sinus Tachycardia with S1Q3T3'})
        ),
        (
            'HP010', 'Evelyn Vasquez', 51, 'A+', 'Female', 'D001',
            'Refractory Takotsubo Stress Cardiomyopathy',
            'Synthetic: Severe bereavement stress triggered acute crushing substernal chest discomfort mimicking anterior STEMI.',
            'DEMO-ECG-010: Diffuse symmetrical deep T-wave inversions across V2-V6, I, aVL. Marked QTc prolongation (510 ms).',
            'Echo: Classical apical ballooning with hypercontractile basal segments, dynamic LVOT gradient 38 mmHg. LVEF 32%.',
            'Troponin-I: 1.1 ng/mL | BNP: 2,400 pg/mL | Coronary Angiogram: Normal coronaries without obstruction',
            json.dumps([
                {'drug': 'Metoprolol Succinate', 'dose': '25 mg', 'route': 'Oral', 'frequency': 'Daily'},
                {'drug': 'Lisinopril', 'dose': '5 mg', 'route': 'Oral', 'frequency': 'Daily'}
            ]),
            'Emergency Contact: Carlos Vasquez (Brother) - Synthetic Tel 555-0200',
            'HIGHLY_CONFIDENTIAL',
            json.dumps({'heart_rate': 94, 'blood_pressure': '102/68 mmHg', 'spo2': '95%', 'temp': '36.8 C', 'resp_rate': 19, 'rhythm': 'Sinus with Deep T Inversions'})
        ),
        (
            'HP011', 'Julian Vance', 65, 'AB-', 'Male', 'D002',
            'Severe Dilated Cardiomyopathy s/p BiV-ICD Optimization',
            'Synthetic: Chronic ischemic cardiomyopathy with refractory NYHA Class III symptoms.',
            'DEMO-ECG-011: Biventricular paced rhythm with 100% ventricular capture.',
            'Echo: LVEF 26%, dyssynchrony improved post-CRT programming.',
            'Serum Creatinine: 1.6 mg/dL | NT-proBNP: 3,400 pg/mL',
            json.dumps([
                {'drug': 'Sacubitril/Valsartan', 'dose': '49/51 mg', 'route': 'Oral', 'frequency': 'Twice daily'},
                {'drug': 'Carvedilol', 'dose': '12.5 mg', 'route': 'Oral', 'frequency': 'Twice daily'}
            ]),
            'Emergency Contact: Laura Vance (Wife) - Synthetic Tel 555-0201',
            'NORMAL',
            json.dumps({'heart_rate': 72, 'blood_pressure': '110/70 mmHg', 'spo2': '96%', 'temp': '36.7 C', 'resp_rate': 18, 'rhythm': 'Biventricular Paced Rhythm'})
        ),
        (
            'HP012', 'Meera Sundaram', 59, 'B+', 'Female', 'D003',
            'Hypertrophic Obstructive Cardiomyopathy (HOCM) with Severe LVOT Gradient',
            'Synthetic: Familial sarcomeric hypertrophic cardiomyopathy with exertional dyspnea and pre-syncope.',
            'DEMO-ECG-012: Giant dagger-like septal Q waves in lateral leads (I, aVL, V5-V6) and massive LVH voltages.',
            'Echo: Asymmetric septal hypertrophy (septum 24mm), SAM of anterior mitral leaflet, resting LVOT gradient 68 mmHg. LVEF 65%.',
            'Hs-Troponin-I: 0.08 ng/mL | Genetic Marker: MYBPC3 Mutation Positive',
            json.dumps([
                {'drug': 'Mavacamten', 'dose': '5 mg', 'route': 'Oral', 'frequency': 'Once daily with monitoring'},
                {'drug': 'Bisoprolol', 'dose': '5 mg', 'route': 'Oral', 'frequency': 'Once daily'}
            ]),
            'Emergency Contact: Suresh Sundaram (Husband) - Synthetic Tel 555-0202',
            'CONFIDENTIAL',
            json.dumps({'heart_rate': 68, 'blood_pressure': '124/76 mmHg', 'spo2': '98%', 'temp': '36.8 C', 'resp_rate': 16, 'rhythm': 'Sinus with Massive LVH Voltages'})
        )
    ]

    expanded_patients = []
    for p in patients:
        pid_num = int(p[0].replace('HP', ''))
        photo = f"pat_hp{pid_num:03d}.svg"
        phone = f"+1 (555) 019-1{pid_num:03d}"
        expanded_patients.append((
            p[0], p[1], photo, p[2], p[3], p[4], p[5], p[6], p[7], p[8],
            p[9], p[10], phone, p[11], p[12], p[13], p[14]
        ))

    cursor.executemany('''
        INSERT INTO patients (
            patient_id, name, profile_photo, age, blood_group, gender, assigned_doctor_id,
            heart_condition_category, medical_history, ecg_report, echo_report,
            blood_test_report, current_prescriptions, phone_number, emergency_contact,
            record_sensitivity_level, vitals, status, is_decoy
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 0)
    ''', expanded_patients)

    # =========================================================================
    # 4. DOCTOR-PATIENT ASSIGNMENTS
    # =========================================================================
    assignments = [
        ('D001', 'HP001'),
        ('D001', 'HP002'),
        ('D001', 'HP010'),
        ('D002', 'HP003'),
        ('D002', 'HP004'),
        ('D002', 'HP011'),
        ('D003', 'HP005'),
        ('D003', 'HP012'),
        ('D004', 'HP006'),
        ('D004', 'HP007'),
        ('D005', 'HP008'),
        ('D005', 'HP009'),
        ('D006', 'HP002'),
        ('D007', 'HP008'),
        ('D008', 'HP004')
    ]
    cursor.executemany('''
        INSERT INTO doctor_patient_assignments (doctor_id, patient_id)
        VALUES (?, ?)
    ''', assignments)

    # =========================================================================
    # 5. CONFIDENTIAL RECORDS TABLE
    # =========================================================================
    confidential_records = [
        ('HP002', 'CONFIDENTIAL', 'VIP Arrhythmia Gene Mutation Panel', 'Genetic sequencing identifies KCNH2 potassium channel variant predisposing to acquired long QT syndrome. Restricted to attending electrophysiologist.', 'CONFIDENTIAL', 'Clinical Genetics Privacy Policy'),
        ('HP004', 'HIGHLY_CONFIDENTIAL', 'Mechanical Circulatory Support & Urgent Transplant Protocol', 'Urgent UNOS Status 1A heart transplant evaluation notes. Biopsy histology and HLA antibody profiling enclosed.', 'HIGHLY_CONFIDENTIAL', 'Organ Transplant Donor Matching Privacy'),
        ('HP006', 'CONFIDENTIAL', 'Leadless Pacemaker Clinical Trial Consent & Device Cryptographic Keys', 'Cryptographic pairing tokens for experimental dual-chamber leadless pulse generator. Restrict access to senior pacemaker specialist.', 'CONFIDENTIAL', 'Medical Device Cybersecurity Directive'),
        ('HP009', 'CONFIDENTIAL', 'Investigational Thrombolytic Titration Log', 'Clinical research phase III protocol for selective catheter-directed acoustic pulse thrombolysis.', 'CONFIDENTIAL', 'Investigational Drug Regulatory Secrecy'),
        ('HP010', 'HIGHLY_CONFIDENTIAL', 'Neurological Stress Neurotransmitter Biomarker Panel', 'Investigational CSF and plasma catecholamine surges under stress cardiomyopathy protocol. Admin/Senior approval required.', 'HIGHLY_CONFIDENTIAL', 'Institutional Review Board Confidential Protocol'),
        ('HP012', 'CONFIDENTIAL', 'Sarcomeric Gene Carrier Family Registry', 'Family pedigree tracking MYBPC3 truncating mutation across three generations. Strict familial genetic privacy.', 'CONFIDENTIAL', 'HIPAA/GINA Genetic Non-Discrimination Privacy')
    ]
    cursor.executemany('''
        INSERT INTO confidential_records (patient_id, sensitivity_level, title, confidential_notes, required_permission, restricted_reason)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', confidential_records)

    # =========================================================================
    # 6. MEDICAL RECORDS (PROGRESS NOTES)
    # =========================================================================
    med_records = [
        ('HP001', 'PROGRESS_NOTE', 'Patient successfully underwent emergency primary PCI. Stent placed in proximal LAD with TIMI 3 flow restored. Strict ICU telemetry monitoring.', 'D001'),
        ('HP002', 'PROGRESS_NOTE', 'Amiodarone infusion initiated. Cardioversion pads placed. Electrophysiology study scheduled for revision of ICD parameters.', 'D001'),
        ('HP003', 'PROGRESS_NOTE', 'Intravenous diuresis producing 2.2L net negative balance. JVP down to 6cm. Titrating ACE inhibitors as hemodynamics allow.', 'D002'),
        ('HP004', 'PROGRESS_NOTE', 'Heparin anticoagulation maintained at PTT 65-80s to prevent apical clot embolization. Transplant coordinator engaged.', 'D002'),
        ('HP005', 'PROGRESS_NOTE', 'Emergency TAVR valve sizing completed via cardiac CT. Aortic valve area severely compromised. Norepinephrine weaning underway.', 'D003'),
        ('HP006', 'PROGRESS_NOTE', 'Temporary transvenous pacing wire actively placed via right IJ. Rate locked at 70 bpm. Permanent pacemaker implantation scheduled.', 'D004'),
        ('HP007', 'PROGRESS_NOTE', 'Cardiothoracic surgical consultation completed. Valve replacement indicated due to mobile 14mm vegetation and leaflet flail.', 'D004'),
        ('HP008', 'PROGRESS_NOTE', 'Pre-procedure 3D cardiac reconstruction for transcatheter pulmonary valve replacement (TPVR). Right ventricular pressures stable.', 'D005'),
        ('HP009', 'PROGRESS_NOTE', 'Systemic thrombolysis completed. Significant improvement in arterial oxygenation (PaO2 88 on 4L). Echocardiogram demonstrates resolving RV strain.', 'D005'),
        ('HP010', 'PROGRESS_NOTE', 'Telemetry free from sustained ventricular arrhythmias. Beta-blockade well tolerated. Repeat echo demonstrates improving apical wall motion.', 'D001')
    ]
    cursor.executemany('''
        INSERT INTO medical_records (patient_id, record_type, clinical_notes, recorded_by_doctor_id)
        VALUES (?, ?, ?, ?)
    ''', med_records)

    # =========================================================================
    # 7. DECOY / HONEYPOT PATIENTS (At least 10 isolated fake records)
    # =========================================================================
    decoy_patients = [
        (
            'HP-DEC-101', 'Demo Patient 1042', 58, 'O+', 'Male', 'D-DECOY-99',
            'Synthetic Cardiac Case - Canary #01',
            'SYNTHETIC HONEYTOKEN RECORD: This profile contains zero actual clinical patient data. Deployed to detect unauthorized health data exfiltration.',
            'DEMO-ECG-1042: Synthetic test waveform generated for decoy cybersecurity monitoring.',
            'Decoy Echo: Normal baseline synthetic dimensions.',
            'Synthetic Marker Alpha: 999.0 AU (Decoy Reference) | Canary Flag: ACTIVE_TRAP',
            json.dumps([{'drug': 'Placebo Decoy Statin', 'dose': '20 mg', 'route': 'Oral', 'frequency': 'Daily'}]),
            'Emergency Contact: Decoy Trap Monitor - Tel 555-0001',
            json.dumps({'heart_rate': 88, 'blood_pressure': '120/80 mmHg', 'spo2': '98%', 'temp': '37.0 C', 'resp_rate': 18}),
            'CANARY-SIG-1042-HONEYPOT-PATIENT'
        ),
        (
            'HP-DEC-102', 'Demo Patient 1088 (VIP Canary)', 63, 'AB-', 'Female', 'D-DECOY-99',
            'Synthetic VIP Cardiac Profile - High-Attraction Honeypot',
            'SYNTHETIC HONEYTOKEN RECORD: Specially tagged high-value target decoy designed to entice unauthorized database scrapers.',
            'DEMO-ECG-1088: Decoy cardiac trace with embedded cybersecurity audit watermark.',
            'Decoy Echo: Synthetic artificial parameters.',
            'Canary Hydro-Marker: 77.7 | Watermark: TRAPPED',
            json.dumps([{'drug': 'Synthetic Cardioprotect', 'dose': '10 mg', 'route': 'Oral', 'frequency': 'Twice Daily'}]),
            'Emergency Contact: VIP Sandbox Sentinel - Tel 555-0002',
            json.dumps({'heart_rate': 95, 'blood_pressure': '135/85 mmHg', 'spo2': '97%', 'temp': '36.9 C', 'resp_rate': 19}),
            'CANARY-SIG-1088-VIP-HONEYTOKEN'
        ),
        (
            'HP-DEC-103', 'Demo Patient 1099 (Canary Trauma)', 47, 'B+', 'Male', 'D-DECOY-99',
            'Synthetic Post-Resuscitation Canary Record',
            'SYNTHETIC HONEYTOKEN RECORD: Isolated demo sandbox entry. Not for clinical usage.',
            'DEMO-ECG-1099: Artificial test pattern for cybersecurity threat mitigation analysis.',
            'Decoy Echo: Baseline mock test values.',
            'Synthetic Troponin Sim: 0.05 | Trap Status: ACTIVE',
            json.dumps([{'drug': 'Synthetic Aspirin Sim', 'dose': '100 mg', 'route': 'Oral', 'frequency': 'Daily'}]),
            'Emergency Contact: Decoy Isolation - Tel 555-0003',
            json.dumps({'heart_rate': 105, 'blood_pressure': '110/70 mmHg', 'spo2': '95%', 'temp': '37.1 C', 'resp_rate': 21}),
            'CANARY-SIG-1099-RESUSCITATION'
        ),
        (
            'HP-DEC-104', 'Demo Patient 1100 (SQLi Trap)', 71, 'O-', 'Female', 'D-DECOY-99',
            'Synthetic Aortic Dissection Canary Record',
            'SYNTHETIC HONEYTOKEN RECORD: Trap record deployed for SQL injection & enumeration detection.',
            'DEMO-ECG-1100: Synthetic trace.',
            'Decoy Echo: Synthetic baseline.',
            'Decoy D-Dimer: 5.0 | Exploit Tripwire: PRIMED',
            json.dumps([{'drug': 'Decoy Labetalol', 'dose': '20 mg', 'route': 'IV', 'frequency': 'Stat'}]),
            'Emergency Contact: SQL Injection Canary - Tel 555-0004',
            json.dumps({'heart_rate': 120, 'blood_pressure': '160/95 mmHg', 'spo2': '93%', 'temp': '37.2 C', 'resp_rate': 24}),
            'CANARY-SIG-1100-SQLI-TRAP'
        ),
        (
            'HP-DEC-105', 'Demo Patient 1105 (Behavioral Lure)', 52, 'A+', 'Male', 'D-DECOY-99',
            'Synthetic Arrhythmia Canary Lure',
            'SYNTHETIC HONEYTOKEN RECORD: Behavioral entrapment trap node.',
            'DEMO-ECG-1105: Synthetic baseline.',
            'Decoy Echo: Normal baseline simulation.',
            'Decoy Potassium: 4.0 | Sandbox ID: LURE-05',
            json.dumps([{'drug': 'Decoy Multivitamin', 'dose': '1 tab', 'route': 'Oral', 'frequency': 'Daily'}]),
            'Emergency Contact: Behavioral Sandbox - Tel 555-0005',
            json.dumps({'heart_rate': 75, 'blood_pressure': '125/80 mmHg', 'spo2': '98%', 'temp': '36.8 C', 'resp_rate': 17}),
            'CANARY-SIG-1105-BEHAVIORAL'
        ),
        (
            'HP-DEC-106', 'Demo Patient 1111 (Golden Master Bait)', 60, 'B+', 'Female', 'D-DECOY-99',
            'Synthetic Golden Honeypot Master Canary',
            'SYNTHETIC HONEYTOKEN RECORD: Flagship high-priority canary bait record for bulk scrapers.',
            'DEMO-ECG-1111: Distinctive honeypot trap waveform.',
            'Decoy Echo: Marked trap signature.',
            'Exfiltration Marker: TRIPPED | Alert Level: CRITICAL',
            json.dumps([{'drug': 'Trap Compound X', 'dose': '100 mg', 'route': 'Oral', 'frequency': 'Stat'}]),
            'Emergency Contact: Exfiltration Trap Sentinel - Tel 555-0006',
            json.dumps({'heart_rate': 110, 'blood_pressure': '95/60 mmHg', 'spo2': '91%', 'temp': '37.3 C', 'resp_rate': 23}),
            'CANARY-SIG-1111-GOLDEN-MASTER'
        ),
        (
            'HP-DEC-107', 'Demo Patient 1115 (Shadow Canary)', 66, 'AB+', 'Male', 'D-DECOY-99',
            'Synthetic Dilated Cardiomyopathy Decoy',
            'SYNTHETIC HONEYTOKEN RECORD: Shadow sandbox canary.',
            'DEMO-ECG-1115: Synthetic trace.',
            'Decoy Echo: Artificial dimensions.',
            'Marker: CANARY-ACTIVE',
            json.dumps([{'drug': 'Decoy Placebo Beta', 'dose': '5 mg', 'route': 'Oral', 'frequency': 'Daily'}]),
            'Emergency Contact: Shadow Sentinel - Tel 555-0007',
            json.dumps({'heart_rate': 82, 'blood_pressure': '115/75 mmHg', 'spo2': '97%', 'temp': '36.8 C', 'resp_rate': 18}),
            'CANARY-SIG-1115-SHADOW'
        ),
        (
            'HP-DEC-108', 'Demo Patient 1120 (Scraper Trap)', 49, 'O+', 'Female', 'D-DECOY-99',
            'Synthetic Valvular Heart Disease Decoy',
            'SYNTHETIC HONEYTOKEN RECORD: Deployed for automated scraper detection.',
            'DEMO-ECG-1120: Fake waveform pattern.',
            'Decoy Echo: Synthetic.',
            'Marker: BOT-TRIPPED',
            json.dumps([{'drug': 'Decoy Placebo Gamma', 'dose': '10 mg', 'route': 'Oral', 'frequency': 'Daily'}]),
            'Emergency Contact: Scraper Honeytrap - Tel 555-0008',
            json.dumps({'heart_rate': 88, 'blood_pressure': '122/78 mmHg', 'spo2': '96%', 'temp': '37.0 C', 'resp_rate': 19}),
            'CANARY-SIG-1120-SCRAPER'
        ),
        (
            'HP-DEC-109', 'Demo Patient 1125 (Telemetry Decoy)', 55, 'A-', 'Male', 'D-DECOY-99',
            'Synthetic Ischemic Heart Disease Canary',
            'SYNTHETIC HONEYTOKEN RECORD: Monitored honeytoken sandbox node.',
            'DEMO-ECG-1125: Artificial waveform.',
            'Decoy Echo: Fake parameters.',
            'Marker: TELEMETRY-LURE',
            json.dumps([{'drug': 'Decoy Placebo Delta', 'dose': '25 mg', 'route': 'Oral', 'frequency': 'Daily'}]),
            'Emergency Contact: Telemetry Trap - Tel 555-0009',
            json.dumps({'heart_rate': 92, 'blood_pressure': '130/82 mmHg', 'spo2': '95%', 'temp': '36.9 C', 'resp_rate': 20}),
            'CANARY-SIG-1125-TELEMETRY'
        ),
        (
            'HP-DEC-110', 'Demo Patient 1130 (Exfiltration Canary)', 73, 'B-', 'Female', 'D-DECOY-99',
            'Synthetic Cardiac Arrest Canary Record',
            'SYNTHETIC HONEYTOKEN RECORD: Zero-tolerance exfiltration trap.',
            'DEMO-ECG-1130: Artificial rhythm.',
            'Decoy Echo: Artificial.',
            'Marker: EXFIL-TRIPWIRE',
            json.dumps([{'drug': 'Decoy Placebo Epsilon', 'dose': '50 mg', 'route': 'Oral', 'frequency': 'Daily'}]),
            'Emergency Contact: Exfil Trap Monitor - Tel 555-0010',
            json.dumps({'heart_rate': 100, 'blood_pressure': '100/65 mmHg', 'spo2': '94%', 'temp': '37.1 C', 'resp_rate': 22}),
            'CANARY-SIG-1130-EXFIL'
        )
    ]

    expanded_decoys = []
    for d in decoy_patients:
        did_num = d[0].replace('HP-DEC-', '')
        photo = f"dec_{did_num}.svg"
        phone = f"+1 (555) 019-9{did_num}"
        expanded_decoys.append((
            d[0], d[1], photo, d[2], d[3], d[4], d[5], d[6], d[7], d[8],
            d[9], d[10], d[11], phone, d[12], d[13], d[14]
        ))

    cursor.executemany('''
        INSERT INTO decoy_patients (
            patient_id, name, profile_photo, age, blood_group, gender, assigned_doctor,
            heart_condition_category, medical_history, ecg_report, echo_report,
            blood_test_report, current_prescriptions, phone_number, emergency_contact,
            vitals, honeytoken_tag, status, is_decoy
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 1)
    ''', expanded_decoys)

    # =========================================================================
    # 8. DECOY RECORDS
    # =========================================================================
    decoy_records = [
        ('HP-DEC-101', 'Synthetic Canary #01', 'Decoy medical chart created to detect unauthorized access.'),
        ('HP-DEC-102', 'Synthetic VIP Canary', 'High-attraction honeytoken node deployed for adversary attribution.'),
        ('HP-DEC-104', 'Synthetic SQLi Trap', 'Canary profile monitoring database query enumeration.')
    ]
    cursor.executemany('''
        INSERT INTO decoy_records (decoy_patient_id, fake_diagnosis, fake_clinical_notes)
        VALUES (?, ?, ?)
    ''', decoy_records)

    # =========================================================================
    # 9. INITIAL AUDIT LOGS (25+ Detailed Records)
    # =========================================================================
    now = datetime.now()
    audit_samples = [
        ((now - timedelta(hours=6, minutes=45)).strftime('%Y-%m-%d %H:%M:%S'), 'U_DOC01', 'doctor', 'HP001', 'LOGIN_SUCCESS', '192.168.1.101', 'TRUSTED', 10, 'LOW', 'SUCCESS', None, 'sess-doc01-01', 'Doctor Lin authenticated via Demo MFA on trusted ICU terminal'),
        ((now - timedelta(hours=6, minutes=40)).strftime('%Y-%m-%d %H:%M:%S'), 'U_DOC01', 'doctor', 'HP001', 'VIEW_PATIENT_RECORD', '192.168.1.101', 'TRUSTED', 10, 'LOW', 'SUCCESS', None, 'sess-doc01-01', 'Doctor Lin accessed assigned patient Arthur Pendelton (HP001) chart'),
        ((now - timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S'), 'U_DOC02', 'doctor', 'HP003', 'LOGIN_SUCCESS', '192.168.1.102', 'TRUSTED', 10, 'LOW', 'SUCCESS', None, 'sess-doc02-01', 'Doctor Vance authenticated via Demo MFA on CCU station'),
        ((now - timedelta(hours=5, minutes=25)).strftime('%Y-%m-%d %H:%M:%S'), 'U_DOC02', 'doctor', 'HP003', 'VIEW_PATIENT_RECORD', '192.168.1.102', 'TRUSTED', 10, 'LOW', 'SUCCESS', None, 'sess-doc02-01', 'Doctor Vance viewed assigned patient Marcus Thorne (HP003) record'),
        ((now - timedelta(hours=4, minutes=50)).strftime('%Y-%m-%d %H:%M:%S'), 'U_DOC01', 'doctor', 'HP003', 'UNAUTHORIZED_PATIENT_ACCESS', '192.168.1.101', 'TRUSTED', 65, 'HIGH', 'DENIED', 'CROSS_PATIENT_ACCESS', 'sess-doc01-01', 'Doctor Lin attempted to access HP003 assigned strictly to Doctor Vance. Access blocked.'),
        ((now - timedelta(hours=4, minutes=15)).strftime('%Y-%m-%d %H:%M:%S'), 'UNKNOWN', 'unauthenticated', None, 'LOGIN_FAILED', '198.51.100.42', 'UNKNOWN', 55, 'MEDIUM', 'DENIED', 'BRUTE_FORCE_LOGIN', 'sess-atk-01', 'Failed password attempt for user: admin_demo (Credential stuffing indicator)'),
        ((now - timedelta(hours=4, minutes=14)).strftime('%Y-%m-%d %H:%M:%S'), 'UNKNOWN', 'unauthenticated', None, 'LOGIN_FAILED', '198.51.100.42', 'UNKNOWN', 80, 'HIGH', 'DENIED', 'BRUTE_FORCE_LOGIN', 'sess-atk-01', '2nd failed password attempt from unknown device'),
        ((now - timedelta(hours=4, minutes=13)).strftime('%Y-%m-%d %H:%M:%S'), 'UNKNOWN', 'unauthenticated', None, 'LOGIN_FAILED', '198.51.100.42', 'UNKNOWN', 95, 'CRITICAL', 'DECOY_SERVED', 'BRUTE_FORCE_LOGIN', 'sess-atk-01', '3rd consecutive failed login. Threshold crossed. Shunted to Decoy sandbox.'),
        ((now - timedelta(hours=4, minutes=10)).strftime('%Y-%m-%d %H:%M:%S'), 'UNKNOWN', 'unauthenticated', 'HP-DEC-101', 'DECOY_RECORD_VIEWED', '198.51.100.42', 'UNKNOWN', 95, 'CRITICAL', 'DECOY_SERVED', 'DECOY_INTERACTION', 'sess-atk-01', 'Attacker interacted with fake patient HP-DEC-101 in honeypot sandbox'),
        ((now - timedelta(hours=3, minutes=30)).strftime('%Y-%m-%d %H:%M:%S'), 'U_ADMIN01', 'admin', None, 'LOGIN_SUCCESS', '192.168.1.2', 'TRUSTED', 5, 'LOW', 'SUCCESS', None, 'sess-adm-01', 'Security Administrator Hayes authenticated with Demo MFA'),
        ((now - timedelta(hours=3, minutes=25)).strftime('%Y-%m-%d %H:%M:%S'), 'U_ADMIN01', 'admin', None, 'VIEW_SECURITY_DASHBOARD', '192.168.1.2', 'TRUSTED', 5, 'LOW', 'SUCCESS', None, 'sess-adm-01', 'Admin Hayes queried real-time threat telemetry and active decoy sessions'),
        ((now - timedelta(hours=2, minutes=45)).strftime('%Y-%m-%d %H:%M:%S'), 'U_DOC03', 'doctor', 'HP004', 'HIGHLY_CONFIDENTIAL_ACCESS_DENIED', '192.168.1.103', 'TRUSTED', 70, 'HIGH', 'DENIED', 'CONFIDENTIAL_RECORD_PROBE', 'sess-doc03-01', 'Resident Dr. Rostova attempted accessing HIGHLY_CONFIDENTIAL transplant protocol HP004. Clearance insufficient.'),
        ((now - timedelta(hours=2, minutes=10)).strftime('%Y-%m-%d %H:%M:%S'), 'U_DOC01', 'doctor', 'HP005', 'EMERGENCY_ACCESS', '192.168.1.101', 'TRUSTED', 25, 'LOW', 'SUCCESS', 'EMERGENCY_BREAK_GLASS', 'sess-doc01-02', 'Emergency Break-Glass Access: Dr. Lin requested temporary emergency chart access for HP005 (Reason: Cardiogenic shock resuscitation in transit).'),
        ((now - timedelta(hours=1, minutes=40)).strftime('%Y-%m-%d %H:%M:%S'), 'U_DOC02', 'doctor', None, 'BULK_ACCESS_DETECTED', '192.168.1.102', 'TRUSTED', 85, 'CRITICAL', 'FLAGGED', 'INSIDER_THREAT', 'sess-doc02-02', 'Insider Threat Alert: Dr. Vance executed rapid bulk queries across 9 unrelated cardiac records in 4.2 seconds. Restricting access to decoy.')
    ]

    cursor.executemany('''
        INSERT INTO audit_logs (
            timestamp, user_id, role, patient_id, action, ip_address,
            device_status, risk_score, risk_level, result, threat_type,
            session_id, details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', audit_samples)

    # =========================================================================
    # 10. SECURITY ALERTS
    # =========================================================================
    alerts = [
        ('ALT-2026-001', 'Brute Force Credential Stuffing', 'CRITICAL', 'UNKNOWN', (now - timedelta(hours=4, minutes=13)).strftime('%Y-%m-%d %H:%M:%S'), 95, '3 consecutive failed authentication requests against admin_demo. IP blacklisted and directed to Honeytoken Chamber.', 'INVESTIGATING'),
        ('ALT-2026-002', 'Unauthorized Cross-Patient Access Attempt', 'HIGH', 'U_DOC01', (now - timedelta(hours=4, minutes=50)).strftime('%Y-%m-%d %H:%M:%S'), 65, 'Doctor Lin (D001) attempted to access patient HP003 assigned strictly to Doctor Vance (D002). Access was blocked.', 'RESOLVED'),
        ('ALT-2026-003', 'Insufficient Permission: Highly Confidential Record', 'HIGH', 'U_DOC03', (now - timedelta(hours=2, minutes=45)).strftime('%Y-%m-%d %H:%M:%S'), 70, 'Resident Dr. Rostova attempted to view HIGHLY_CONFIDENTIAL heart transplant protocol HP004. Access denied.', 'NEW'),
        ('ALT-2026-004', 'Insider Threat: Rapid Bulk Scraping Behavior', 'CRITICAL', 'U_DOC02', (now - timedelta(hours=1, minutes=40)).strftime('%Y-%m-%d %H:%M:%S'), 85, 'Authorized clinician Dr. Vance initiated rapid query burst on 9 unassigned patient records. Access temporarily shunted to honeypot.', 'INVESTIGATING'),
        ('ALT-2026-005', 'Honeytoken Canary Tripwire Triggered', 'CRITICAL', 'UNKNOWN', (now - timedelta(hours=4, minutes=10)).strftime('%Y-%m-%d %H:%M:%S'), 98, 'Canary patient HP-DEC-101 queried by external suspicious host. Real patient database shielded.', 'INVESTIGATING')
    ]
    cursor.executemany('''
        INSERT INTO security_alerts (alert_id, threat_type, severity, user_id, timestamp, risk_score, description, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', alerts)

    # =========================================================================
    # 11. DECOY SESSIONS
    # =========================================================================
    decoy_sessions = [
        ('SESS-DEC-99120', 'UNKNOWN', '198.51.100.42', (now - timedelta(hours=4, minutes=10)).strftime('%Y-%m-%d %H:%M:%S'), 'HP-DEC-101', 'HP-DEC-101', 'SEARCH_AND_VIEW_CANARY', 4, 95, 'CRITICAL'),
        ('SESS-DEC-88143', 'UNKNOWN', '203.0.113.88', (now - timedelta(hours=3, minutes=15)).strftime('%Y-%m-%d %H:%M:%S'), 'HP-DEC-102', 'HP-DEC-102', 'VIP_CANARY_EXFILTRATION_PROBE', 6, 98, 'CRITICAL'),
        ('SESS-DEC-77112', 'U_DOC02', '192.168.1.102', (now - timedelta(hours=1, minutes=38)).strftime('%Y-%m-%d %H:%M:%S'), 'HP-DEC-106', 'HP-DEC-106', 'BULK_QUERY_SHUNTED_TO_HONEYPOT', 9, 85, 'CRITICAL')
    ]
    cursor.executemany('''
        INSERT INTO decoy_sessions (decoy_session_id, user_id, ip_address, timestamp, fake_patient_searched, fake_record_viewed, actions_performed, request_count, risk_score, threat_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', decoy_sessions)

    # =========================================================================
    # 12. EMERGENCY BREAK-GLASS SAMPLE RECORD
    # =========================================================================
    emergency_samples = [
        ('D001', 'HP005', 'sess-doc01-02', 'Emergent cardiogenic shock resuscitation in transit; primary physician unreachable', (now - timedelta(hours=2, minutes=10)).strftime('%Y-%m-%d %H:%M:%S'), (now + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S'), 10, 25, 1, 'ACTIVE')
    ]
    cursor.executemany('''
        INSERT INTO emergency_access (doctor_id, patient_id, session_id, reason, requested_at, expires_at, risk_score_before, risk_score_after, approved, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', emergency_samples)

    conn.commit()
    print("Database seeding completed successfully.")

if __name__ == '__main__':
    seed()
