import json
import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

try:
    from database.db import get_db as get_conn
except ImportError:
    try:
        from db import get_db as get_conn
    except ImportError:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from database.db import get_db as get_conn

def get_db():
    return get_conn()

def seed_database():
    """Populates synthetic data for doctors, patients, decoys, audit logs, and security events."""
    conn = get_db()
    cursor = conn.cursor()

    # Clear existing tables to ensure clean state
    tables = [
        'users', 'real_patients', 'decoy_patients', 'doctor_patient_assignments',
        'audit_logs', 'security_events', 'decoy_interactions', 'failed_attempts'
    ]
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")

    # =========================================================================
    # 1. USERS: 1 Admin + 5 Synthetic Cardiologists
    # =========================================================================
    users_data = [
        (
            'ADMIN001', 'admin', generate_password_hash('AdminSecure#2026!'),
            'Alex Hayes, CISSP', 'admin', 'Cybersecurity Director', 'Health-Sec Operations',
            'alex.hayes@heartsec.internal', 'active', '2026-10-05 14:10:00'
        ),
        (
            'DOC101', 'dr_roberts', generate_password_hash('Doctor#101'),
            'Dr. Emily Roberts, MD', 'doctor', 'Interventional Cardiology', 'Cardiology ICU',
            'emily.roberts@cardio.internal', 'active', '2026-10-05 14:32:00'
        ),
        (
            'DOC102', 'dr_chang', generate_password_hash('Doctor#102'),
            'Dr. Michael Chang, MD', 'doctor', 'Electrophysiology', 'Cardiac Arrhythmia Unit',
            'michael.chang@cardio.internal', 'active', '2026-10-05 13:45:00'
        ),
        (
            'DOC103', 'dr_mansoor', generate_password_hash('Doctor#103'),
            'Dr. Sarah Al-Mansoor, MD', 'doctor', 'Heart Failure & Transplant', 'Advanced Heart Failure Unit',
            'sarah.mansoor@cardio.internal', 'active', '2026-10-05 11:20:00'
        ),
        (
            'DOC104', 'dr_patel', generate_password_hash('Doctor#104'),
            'Dr. Rajesh Patel, MD', 'doctor', 'Pediatric & Congenital Cardiology', 'Cardiac Critical Care',
            'rajesh.patel@cardio.internal', 'active', '2026-10-05 10:15:00'
        ),
        (
            'DOC105', 'dr_vance', generate_password_hash('Doctor#105'),
            'Dr. Olivia Vance, MD', 'doctor', 'Cardiac Surgery & Intensive Care', 'Cardiothoracic Surgery',
            'olivia.vance@cardio.internal', 'active', '2026-10-05 09:30:00'
        )
    ]

    cursor.executemany('''
    INSERT INTO users (user_id, username, password_hash, name, role, specialty, department, email, status, last_login)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', users_data)

    # =========================================================================
    # 2. REAL SYNTHETIC HEART PATIENTS (10 Critical Cardiac Cases)
    # =========================================================================
    real_patients_data = [
        (
            'HP-501', 'Arthur Pendelton', 68, 'Male', 'O+',
            'Acute ST-Elevation Myocardial Infarction (Anterior STEMI)', 'CRITICAL',
            '2026-10-03 04:15:00', 'ICU-Bed-01', 'DOC101',
            json.dumps({'heart_rate': 114, 'blood_pressure': '90/60 mmHg', 'spo2': '92%', 'temp': '37.1 C', 'resp_rate': 24, 'rhythm': 'Sinus Tachycardia with ST elevation'}),
            'Synthetic: Prior hypertension, type 2 diabetes mellitus (12 yrs), coronary stent placed 2021.',
            'Penicillin, Contrast Dye',
            'DEMO-ECG-501: Significant ST-segment elevations in V1-V4 (3.5mm). Reciprocal depressions in II, III, aVF. Hyperacute T waves.',
            'Transthoracic Echo: Hypokinesis of anterior and apical left ventricular walls. Left ventricular enlargement.',
            28,
            json.dumps([
                {'test': 'High-Sensitivity Troponin-I', 'value': '14.8 ng/mL', 'reference': '< 0.04 ng/mL', 'status': 'CRITICAL_HIGH'},
                {'test': 'NT-proBNP', 'value': '4,850 pg/mL', 'reference': '< 125 pg/mL', 'status': 'HIGH'},
                {'test': 'Serum Potassium', 'value': '4.1 mEq/L', 'reference': '3.5 - 5.0 mEq/L', 'status': 'NORMAL'},
                {'test': 'Serum Creatinine', 'value': '1.3 mg/dL', 'reference': '0.7 - 1.3 mg/dL', 'status': 'BORDERLINE'}
            ]),
            json.dumps([
                {'drug': 'Aspirin (Chewable)', 'dose': '325 mg', 'route': 'Oral', 'frequency': 'Stat loading dose', 'status': 'Active'},
                {'drug': 'Ticagrelor', 'dose': '90 mg', 'route': 'Oral', 'frequency': 'Twice daily', 'status': 'Active'},
                {'drug': 'Unfractionated Heparin', 'dose': '18 units/kg/hr', 'route': 'IV Infusion', 'frequency': 'Continuous titration', 'status': 'Active'},
                {'drug': 'Atorvastatin', 'dose': '80 mg', 'route': 'Oral', 'frequency': 'Once daily at bedtime', 'status': 'Active'}
            ]),
            'Patient undergoing emergency primary percutaneous coronary intervention (PPCI). Strict hemodynamic telemetry monitoring required.'
        ),
        (
            'HP-502', 'Helena Rostova', 54, 'Female', 'A-',
            'Sustained Monomorphic Ventricular Tachycardia (VT)', 'CRITICAL',
            '2026-10-04 08:30:00', 'ICU-Bed-02', 'DOC102',
            json.dumps({'heart_rate': 178, 'blood_pressure': '82/50 mmHg', 'spo2': '90%', 'temp': '36.8 C', 'resp_rate': 26, 'rhythm': 'Wide Complex Ventricular Tachycardia'}),
            'Synthetic: Non-ischemic dilated cardiomyopathy diagnosed 2023. Prior ablation therapy for atrial flutter.',
            'Sulfa drugs',
            'DEMO-ECG-502: Wide QRS complexes (> 160ms) at 178 bpm. AV dissociation noted with fusion and capture beats.',
            'Echo: Global left ventricular hypokinesis, severe mitral regurgitation (Grade III/IV), paradoxical septal motion.',
            24,
            json.dumps([
                {'test': 'Serum Magnesium', 'value': '1.4 mg/dL', 'reference': '1.7 - 2.2 mg/dL', 'status': 'LOW'},
                {'test': 'Troponin-I', 'value': '0.85 ng/mL', 'reference': '< 0.04 ng/mL', 'status': 'ELEVATED'},
                {'test': 'Serum Potassium', 'value': '3.2 mEq/L', 'reference': '3.5 - 5.0 mEq/L', 'status': 'LOW'},
                {'test': 'Arterial Blood Gas pH', 'value': '7.31', 'reference': '7.35 - 7.45', 'status': 'ACIDOTIC'}
            ]),
            json.dumps([
                {'drug': 'Amiodarone', 'dose': '150 mg in D5W', 'route': 'IV Infusion', 'frequency': 'Over 10 mins stat, then 1 mg/min', 'status': 'Active'},
                {'drug': 'Magnesium Sulfate', 'dose': '2 g', 'route': 'IV Piggyback', 'frequency': 'Stat over 20 min', 'status': 'Active'},
                {'drug': 'Potassium Chloride', 'dose': '40 mEq', 'route': 'IV Infusion', 'frequency': 'Slow infusion with monitor', 'status': 'Active'}
            ]),
            'Cardioversion standby prepared. Electrophysiology team evaluating urgent ICD (Implantable Cardioverter-Defibrillator) revision.'
        ),
        (
            'HP-503', 'Marcus Thorne', 72, 'Male', 'B+',
            'Acute Decompensated Heart Failure (Wet & Cold Profile)', 'SEVERE',
            '2026-10-02 11:20:00', 'CCU-Room-04', 'DOC103',
            json.dumps({'heart_rate': 98, 'blood_pressure': '105/65 mmHg', 'spo2': '91% on 4L NC', 'temp': '36.9 C', 'resp_rate': 22, 'rhythm': 'Sinus Rhythm with Frequent PVCs'}),
            'Synthetic: Ischemic cardiomyopathy s/p CABG (2018), chronic kidney disease Stage 3b.',
            'None known',
            'DEMO-ECG-503: Left bundle branch block (LBBB) with QRS width 150ms. Secondary repolarization ST-T abnormalities.',
            'Echo: Severely reduced EF, restrictive filling pattern (E/A ratio > 2.0). Dilated IVC with absent inspiratory collapse.',
            22,
            json.dumps([
                {'test': 'NT-proBNP', 'value': '9,200 pg/mL', 'reference': '< 125 pg/mL', 'status': 'CRITICAL_HIGH'},
                {'test': 'Serum Creatinine', 'value': '2.1 mg/dL', 'reference': '0.7 - 1.3 mg/dL', 'status': 'ELEVATED'},
                {'test': 'Blood Urea Nitrogen', 'value': '48 mg/dL', 'reference': '7 - 20 mg/dL', 'status': 'ELEVATED'}
            ]),
            json.dumps([
                {'drug': 'Furosemide', 'dose': '80 mg', 'route': 'IV Bolus', 'frequency': 'Twice daily', 'status': 'Active'},
                {'drug': 'Sacubitril/Valsartan', 'dose': '24/26 mg', 'route': 'Oral', 'frequency': 'Twice daily (held temporarily)', 'status': 'Paused'},
                {'drug': 'Empagliflozin', 'dose': '10 mg', 'route': 'Oral', 'frequency': 'Daily morning', 'status': 'Active'}
            ]),
            'Aggressive diuresis in progress. Strict fluid restriction to 1.5 L/24h. Daily weight telemetry linked.'
        ),
        (
            'HP-504', 'Sophia Lindqvist', 42, 'Female', 'O-',
            'Severe Peripartum Cardiomyopathy with Apical Thrombus', 'CRITICAL',
            '2026-10-04 15:45:00', 'ICU-Bed-03', 'DOC103',
            json.dumps({'heart_rate': 108, 'blood_pressure': '95/62 mmHg', 'spo2': '94%', 'temp': '37.0 C', 'resp_rate': 20, 'rhythm': 'Sinus Tachycardia'}),
            'Synthetic: 3 weeks postpartum, acute onset progressive orthopnea, nocturnal dyspnea, bilateral lower limb anasarca.',
            'Aspirin (bronchospasm)',
            'DEMO-ECG-504: Sinus tachycardia, biatrial enlargement, non-specific T wave flattenings in lateral leads.',
            'Echo: LVEF 18%. Clear 1.8cm pedunculated apical thrombus. Spontaneous echo contrast in left ventricle.',
            18,
            json.dumps([
                {'test': 'NT-proBNP', 'value': '7,600 pg/mL', 'reference': '< 125 pg/mL', 'status': 'HIGH'},
                {'test': 'D-Dimer', 'value': '1.8 mcg/mL', 'reference': '< 0.5 mcg/mL', 'status': 'ELEVATED'},
                {'test': 'Cardiac Enzymes', 'value': '0.12 ng/mL', 'reference': '< 0.04 ng/mL', 'status': 'BORDERLINE'}
            ]),
            json.dumps([
                {'drug': 'Low Molecular Weight Heparin', 'dose': '1 mg/kg', 'route': 'SubQ', 'frequency': 'Every 12 hours', 'status': 'Active'},
                {'drug': 'Bromocriptine', 'dose': '2.5 mg', 'route': 'Oral', 'frequency': 'Daily', 'status': 'Active'},
                {'drug': 'Carvedilol', 'dose': '3.125 mg', 'route': 'Oral', 'frequency': 'Twice daily', 'status': 'Active'}
            ]),
            'High embolic risk due to mobile apical clot. Heart transplant team notified for backup mechanical circulatory support (Impella/ECMO).'
        ),
        (
            'HP-505', 'Dmitri Volkov', 61, 'Male', 'AB+',
            'Critical Aortic Stenosis with Syncope and Cardiogenic Shock', 'CRITICAL',
            '2026-10-01 19:10:00', 'ICU-Bed-04', 'DOC101',
            json.dumps({'heart_rate': 92, 'blood_pressure': '84/55 mmHg', 'spo2': '93%', 'temp': '36.7 C', 'resp_rate': 22, 'rhythm': 'Sinus rhythm with LV Strain'}),
            'Synthetic: Bicuspid aortic valve history, exertional angina, documented recurrent syncopal episodes.',
            'Codeine',
            'DEMO-ECG-505: Severe LVH by voltage criteria (Sokolow-Lyon index > 42mm). Deep asymmetric T-wave inversions in I, aVL, V5-V6.',
            'Echo: Aortic valve area 0.58 cm2, mean transvalvular pressure gradient 52 mmHg, peak jet velocity 4.8 m/s.',
            30,
            json.dumps([
                {'test': 'Troponin-I', 'value': '0.42 ng/mL', 'reference': '< 0.04 ng/mL', 'status': 'ELEVATED'},
                {'test': 'Lactate', 'value': '2.6 mmol/L', 'reference': '0.5 - 2.0 mmol/L', 'status': 'ELEVATED'},
                {'test': 'CBC Hemoglobin', 'value': '12.4 g/dL', 'reference': '13.5 - 17.5 g/dL', 'status': 'MILD_ANEMIA'}
            ]),
            json.dumps([
                {'drug': 'Norepinephrine', 'dose': '0.05 mcg/kg/min', 'route': 'IV Infusion', 'frequency': 'Titrated to MAP > 65 mmHg', 'status': 'Active'},
                {'drug': 'Furosemide', 'dose': '40 mg', 'route': 'IV Push', 'frequency': 'Daily', 'status': 'Active'}
            ]),
            'Scheduled for urgent emergent TAVR (Transcatheter Aortic Valve Replacement). Avoid aggressive vasodilators.'
        ),
        (
            'HP-506', 'Grace Chen', 79, 'Female', 'O+',
            'Complete Atrioventricular Heart Block (Third-Degree AV Block)', 'CRITICAL',
            '2026-10-05 02:40:00', 'CCU-Room-02', 'DOC102',
            json.dumps({'heart_rate': 34, 'blood_pressure': '78/48 mmHg', 'spo2': '92%', 'temp': '36.4 C', 'resp_rate': 18, 'rhythm': 'Complete Heart Block with Ventricular Escape'}),
            'Synthetic: Degenerative conduction system disease (Lev-Lenègre disease), coronary artery disease.',
            'Iodine',
            'DEMO-ECG-506: Total AV dissociation. P wave rate 84 bpm, ventricular escape rhythm 34 bpm with broad atypical complexes.',
            'Echo: Preserved LVEF 50%, mild aortic regurgitation, normal ventricular dimensions.',
            50,
            json.dumps([
                {'test': 'Serum Potassium', 'value': '4.3 mEq/L', 'reference': '3.5 - 5.0 mEq/L', 'status': 'NORMAL'},
                {'test': 'Thyroid Stimulating Hormone', 'value': '2.1 mIU/L', 'reference': '0.4 - 4.0 mIU/L', 'status': 'NORMAL'},
                {'test': 'Digoxin Level', 'value': '< 0.3 ng/mL', 'reference': '0.8 - 2.0 ng/mL', 'status': 'NON_TOXIC'}
            ]),
            json.dumps([
                {'drug': 'Atropine', 'dose': '1 mg', 'route': 'IV Push', 'frequency': 'Administered in transit', 'status': 'Completed'},
                {'drug': 'Isoproterenol Infusion', 'dose': '2 mcg/min', 'route': 'IV Continuous', 'frequency': 'Bridge to pacemaker', 'status': 'Active'}
            ]),
            'Temporary transvenous pacing wire actively placed via right internal jugular. Dual-chamber permanent pacemaker insertion scheduled today.'
        ),
        (
            'HP-507', 'Liam O Connor', 58, 'Male', 'A+',
            'Subacute Bacterial Endocarditis with Severe Mitral Valve Vegetations', 'SEVERE',
            '2026-10-02 18:00:00', 'CCU-Room-07', 'DOC105',
            json.dumps({'heart_rate': 102, 'blood_pressure': '112/68 mmHg', 'spo2': '95%', 'temp': '38.6 C', 'resp_rate': 20, 'rhythm': 'Sinus Tachycardia'}),
            'Synthetic: Rheumatic heart disease in childhood, dental extraction 4 weeks prior without prophylactic antibiotics.',
            'Cephalosporins',
            'DEMO-ECG-507: Sinus tachycardia with PR interval prolongation (240ms - First-degree AV block, suspecting perivalvular extension).',
            'Transesophageal Echo (TEE): Oscillating 14mm vegetation on anterior mitral leaflet, flail leaflet segment, severe eccentric MR.',
            45,
            json.dumps([
                {'test': 'Blood Culture #1 & #2', 'value': 'Positive for Streptococcus viridans', 'reference': 'Sterile', 'status': 'INFECTIOUS'},
                {'test': 'C-Reactive Protein (CRP)', 'value': '118 mg/L', 'reference': '< 5.0 mg/L', 'status': 'CRITICAL_HIGH'},
                {'test': 'Erythrocyte Sedimentation Rate', 'value': '84 mm/hr', 'reference': '0 - 15 mm/hr', 'status': 'ELEVATED'}
            ]),
            json.dumps([
                {'drug': 'Ampicillin-Sulbactam', 'dose': '3 g', 'route': 'IV Infusion', 'frequency': 'Every 6 hours', 'status': 'Active'},
                {'drug': 'Gentamicin', 'dose': '1 mg/kg', 'route': 'IV Infusion', 'frequency': 'Every 8 hours with trough monitoring', 'status': 'Active'}
            ]),
            'Surgical valve replacement consultation requested due to vegetation size > 10mm and progressive PR prolongation.'
        ),
        (
            'HP-508', 'Fatima Zahra', 36, 'Female', 'B-',
            'Postoperative Tetralogy of Fallot with Free Pulmonary Regurgitation & RV Dysfunction', 'GUARDED',
            '2026-10-04 10:15:00', 'Cardiac-Ward-12', 'DOC104',
            json.dumps({'heart_rate': 78, 'blood_pressure': '118/74 mmHg', 'spo2': '97%', 'temp': '36.6 C', 'resp_rate': 16, 'rhythm': 'Sinus rhythm with RBBB'}),
            'Synthetic: Complete repair of TOF at age 4. Progressive fatigue and reduced exercise capacity over past 6 months.',
            'Latex',
            'DEMO-ECG-508: Classic right bundle branch block (RBBB) pattern with QRS duration 164ms. Right axis deviation (+120 degrees).',
            'Cardiac MRI: Free pulmonary regurgitation (regurgitant fraction 48%), right ventricular end-diastolic volume index 168 mL/m2.',
            48,
            json.dumps([
                {'test': 'BNP Level', 'value': '340 pg/mL', 'reference': '< 100 pg/mL', 'status': 'ELEVATED'},
                {'test': 'Serum Electrolytes', 'value': 'Normal limits', 'reference': 'Normal', 'status': 'NORMAL'}
            ]),
            json.dumps([
                {'drug': 'Spironolactone', 'dose': '25 mg', 'route': 'Oral', 'frequency': 'Once daily', 'status': 'Active'},
                {'drug': 'Bisoprolol', 'dose': '2.5 mg', 'route': 'Oral', 'frequency': 'Once daily', 'status': 'Active'}
            ]),
            'Candidate for Transcatheter Pulmonary Valve (TPVR / Melody Valve) implantation. Pre-procedure 3D cardiac reconstruction complete.'
        ),
        (
            'HP-509', 'Raymond Sterling', 66, 'Male', 'O+',
            'Massive Acute Pulmonary Embolism with Severe Right Ventricular Strain', 'CRITICAL',
            '2026-10-05 06:15:00', 'ICU-Bed-05', 'DOC101',
            json.dumps({'heart_rate': 128, 'blood_pressure': '86/56 mmHg', 'spo2': '88% on 10L Mask', 'temp': '37.2 C', 'resp_rate': 32, 'rhythm': 'Sinus Tachycardia with S1Q3T3'}),
            'Synthetic: Recent orthopedic knee arthroplasty (10 days ago), prolonged immobility, sudden pleuritic chest pain and collapse.',
            'None known',
            'DEMO-ECG-509: Prominent S wave in lead I, Q wave in lead III, inverted T wave in lead III (Classic McGinn-White S1Q3T3 sign). Inverted T waves in V1-V4.',
            'Echo: McConnell sign (RV free wall hypokinesis with preserved apical contractility), severe pulmonary hypertension (RVSP 64 mmHg).',
            38,
            json.dumps([
                {'test': 'High-Sensitivity Troponin-T', 'value': '0.98 ng/mL', 'reference': '< 0.014 ng/mL', 'status': 'HIGH'},
                {'test': 'D-Dimer Quantitative', 'value': '12.4 mcg/mL', 'reference': '< 0.5 mcg/mL', 'status': 'CRITICAL_HIGH'},
                {'test': 'Lactate', 'value': '3.8 mmol/L', 'reference': '0.5 - 2.0 mmol/L', 'status': 'HIGH'}
            ]),
            json.dumps([
                {'drug': 'Alteplase (rt-PA)', 'dose': '100 mg', 'route': 'IV Infusion', 'frequency': 'Over 2 hours emergency thrombolysis', 'status': 'Active'},
                {'drug': 'Unfractionated Heparin', 'dose': '80 units/kg bolus, 18 u/kg/hr', 'route': 'IV Infusion', 'frequency': 'Post-thrombolysis infusion', 'status': 'Active'}
            ]),
            'Systemic thrombolysis initiated. Interventional radiology on standby for catheter-directed embolectomy if refractory.'
        ),
        (
            'HP-510', 'Evelyn Vasquez', 51, 'Female', 'A+',
            'Refractory Takotsubo Cardiomyopathy (Stress-Induced Apical Ballooning)', 'SEVERE',
            '2026-10-04 22:15:00', 'CCU-Room-05', 'DOC103',
            json.dumps({'heart_rate': 94, 'blood_pressure': '102/68 mmHg', 'spo2': '95%', 'temp': '36.8 C', 'resp_rate': 19, 'rhythm': 'Sinus rhythm with Deep T-wave Inversions'}),
            'Synthetic: Severe emotional stress triggered acute crushing substernal chest discomfort mimicking anterior STEMI.',
            'Sulfa',
            'DEMO-ECG-510: Diffuse symmetrical deep T-wave inversions across V2-V6, I, aVL. Marked QTc prolongation (510 ms).',
            'Echo: Classical apical ballooning with hypercontractile basal segments, mild dynamic LV outflow tract (LVOT) obstruction.',
            32,
            json.dumps([
                {'test': 'Troponin-I', 'value': '1.1 ng/mL', 'reference': '< 0.04 ng/mL', 'status': 'MODERATELY_ELEVATED'},
                {'test': 'BNP', 'value': '2,400 pg/mL', 'reference': '< 100 pg/mL', 'status': 'HIGH'},
                {'test': 'Coronary Angiogram', 'value': 'Clean epicardial coronaries without obstructive lesion', 'reference': 'Normal', 'status': 'NON_OBSTRUCTIVE'}
            ]),
            json.dumps([
                {'drug': 'Metoprolol Succinate', 'dose': '25 mg', 'route': 'Oral', 'frequency': 'Daily', 'status': 'Active'},
                {'drug': 'Lisinopril', 'dose': '5 mg', 'route': 'Oral', 'frequency': 'Daily', 'status': 'Active'}
            ]),
            'Close monitoring for ventricular arrhythmias secondary to long QTc. Avoid inotropic adrenergic agents.'
        )
    ]

    cursor.executemany('''
    INSERT INTO real_patients (
        patient_id, name, age, gender, blood_group, diagnosis, condition_severity,
        admission_date, room_no, assigned_doctor_id, vitals, medical_history,
        allergies, ecg_report, echo_findings, lvef_percentage, recent_tests,
        prescriptions, clinical_notes, is_decoy
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', real_patients_data)

    # =========================================================================
    # 3. DECOY / HONEYPOT PATIENTS (Strictly Fake Trap Records)
    # =========================================================================
    decoy_patients_data = [
        (
            'HP-DECOY-1042', 'Demo Patient 1042', 58, 'Male', 'O+',
            'Synthetic Cardiac Case - Honeypot Canary #01', 'CRITICAL',
            '2026-10-01 00:00:00', 'DECOY-CHAMBER-A', 'DOC-DECOY-99',
            json.dumps({'heart_rate': 88, 'blood_pressure': '120/80 mmHg', 'spo2': '98%', 'temp': '37.0 C', 'resp_rate': 18, 'rhythm': 'Synthetic Decoy Rhythm'}),
            'SYNTHETIC HONEYTOKEN RECORD: This profile contains zero actual clinical patient data. Created to detect unauthorized healthcare data exfiltration.',
            'Synthetic Honeytoken Flag #A',
            'DEMO-ECG-1042: Synthetic test waveform generated for decoy cybersecurity environment monitoring.',
            'Decoy Echo findings: Synthetic normal chamber dimensions. No medical validity.',
            55,
            json.dumps([
                {'test': 'Synthetic Marker Alpha', 'value': '999.0 AU', 'reference': 'Decoy Reference', 'status': 'DECOY_FLAG'},
                {'test': 'Canary Indicator', 'value': 'ACTIVE_TRAP', 'reference': 'Security Honeytoken', 'status': 'TRIPWIRE'}
            ]),
            json.dumps([
                {'drug': 'Placebo Decoy Statin', 'dose': '20 mg', 'route': 'Oral', 'frequency': 'Daily', 'status': 'Fake Prescription'},
                {'drug': 'Canary Beta-Blocker', 'dose': '50 mg', 'route': 'Oral', 'frequency': 'Daily', 'status': 'Fake Prescription'}
            ]),
            'DECOY TRAP: Any access, scraping, or exfiltration of this patient ID immediately registers in the Security Admin telemetry.',
            'CANARY-SIG-1042-HONEYPOT-PATIENT'
        ),
        (
            'HP-DECOY-1088', 'Demo Patient 1088 (VIP Canary)', 63, 'Female', 'AB-',
            'Synthetic VIP Cardiac Profile - High-Attraction Honeypot', 'CRITICAL',
            '2026-10-02 00:00:00', 'DECOY-VIP-SUITE', 'DOC-DECOY-99',
            json.dumps({'heart_rate': 95, 'blood_pressure': '135/85 mmHg', 'spo2': '97%', 'temp': '36.9 C', 'resp_rate': 19, 'rhythm': 'Synthetic Decoy Rhythm 1088'}),
            'SYNTHETIC HONEYTOKEN RECORD: Specially tagged high-value target decoy designed to entice unauthorized database scrapers.',
            'Synthetic Honeytoken Flag #B',
            'DEMO-ECG-1088: Decoy cardiac trace with embedded cybersecurity audit watermark.',
            'Decoy Echo findings: Synthetic artificial parameters.',
            50,
            json.dumps([
                {'test': 'Canary Hydro-Marker', 'value': '77.7', 'reference': 'Decoy Reference', 'status': 'DECOY_FLAG'}
            ]),
            json.dumps([
                {'drug': 'Synthetic Cardioprotect', 'dose': '10 mg', 'route': 'Oral', 'frequency': 'Twice Daily', 'status': 'Fake Prescription'}
            ]),
            'DECOY TRAP: High attraction honeytoken. Triggers CRITICAL risk score upon query.',
            'CANARY-SIG-1088-VIP-HONEYTOKEN'
        ),
        (
            'HP-DECOY-1099', 'Demo Patient 1099 (Canary Trauma)', 47, 'Male', 'B+',
            'Synthetic Post-Resuscitation Canary Record', 'SEVERE',
            '2026-10-03 00:00:00', 'DECOY-ISOLATION-03', 'DOC-DECOY-99',
            json.dumps({'heart_rate': 105, 'blood_pressure': '110/70 mmHg', 'spo2': '95%', 'temp': '37.1 C', 'resp_rate': 21, 'rhythm': 'Decoy Tachycardia Trace'}),
            'SYNTHETIC HONEYTOKEN RECORD: Isolated demo sandbox entry. Not for clinical usage.',
            'None',
            'DEMO-ECG-1099: Artificial test pattern for cybersecurity threat mitigation analysis.',
            'Decoy Echo: Baseline synthetic mock test values.',
            40,
            json.dumps([{'test': 'Synthetic Troponin Sim', 'value': '0.05', 'reference': 'Decoy', 'status': 'DECOY_FLAG'}]),
            json.dumps([{'drug': 'Synthetic Aspirin Sim', 'dose': '100 mg', 'route': 'Oral', 'frequency': 'Daily', 'status': 'Fake Prescription'}]),
            'Monitored honeytoken sandbox node.',
            'CANARY-SIG-1099-RESUSCITATION'
        ),
        (
            'HP-DECOY-1100', 'Demo Patient 1100', 71, 'Female', 'O-',
            'Synthetic Aortic Dissection Canary Record', 'CRITICAL',
            '2026-10-03 00:00:00', 'DECOY-SUITE-11', 'DOC-DECOY-99',
            json.dumps({'heart_rate': 120, 'blood_pressure': '160/95 mmHg', 'spo2': '93%', 'temp': '37.2 C', 'resp_rate': 24, 'rhythm': 'Decoy Rhythm'}),
            'SYNTHETIC HONEYTOKEN RECORD: Trap record deployed for SQL injection & enumeration detection.',
            'Synthetic Alert',
            'DEMO-ECG-1100: Synthetic trace.',
            'Decoy Echo: Synthetic.',
            35,
            json.dumps([{'test': 'Decoy D-Dimer', 'value': '5.0', 'reference': 'Decoy', 'status': 'DECOY'}]),
            json.dumps([{'drug': 'Decoy Labetalol', 'dose': '20 mg', 'route': 'IV', 'frequency': 'Stat', 'status': 'Fake'}]),
            'SQL injection canary trap node.',
            'CANARY-SIG-1100-SQLI-TRAP'
        ),
        (
            'HP-DECOY-1105', 'Demo Patient 1105 (Shadow Honeypot)', 52, 'Male', 'A+',
            'Synthetic Arrhythmia Canary', 'GUARDED',
            '2026-10-04 00:00:00', 'DECOY-SHADOW-05', 'DOC-DECOY-99',
            json.dumps({'heart_rate': 75, 'blood_pressure': '125/80 mmHg', 'spo2': '98%', 'temp': '36.8 C', 'resp_rate': 17, 'rhythm': 'Normal Decoy'}),
            'SYNTHETIC HONEYTOKEN RECORD: Behavioral entrapment trap.',
            'None',
            'DEMO-ECG-1105: Synthetic baseline.',
            'Decoy Echo: Normal baseline simulation.',
            60,
            json.dumps([{'test': 'Decoy Potassium', 'value': '4.0', 'reference': 'Decoy', 'status': 'DECOY'}]),
            json.dumps([{'drug': 'Decoy Multivitamin', 'dose': '1 tab', 'route': 'Oral', 'frequency': 'Daily', 'status': 'Fake'}]),
            'Behavioral trap honeypot.',
            'CANARY-SIG-1105-BEHAVIORAL'
        ),
        (
            'HP-DECOY-1111', 'Demo Patient 1111 (Mass Exfiltration Trap)', 60, 'Female', 'B+',
            'Synthetic Golden Honeypot Master Canary', 'CRITICAL',
            '2026-10-05 00:00:00', 'DECOY-CHAMBER-Z', 'DOC-DECOY-99',
            json.dumps({'heart_rate': 110, 'blood_pressure': '95/60 mmHg', 'spo2': '91%', 'temp': '37.3 C', 'resp_rate': 23, 'rhythm': 'Trap Waveform'}),
            'SYNTHETIC HONEYTOKEN RECORD: Flagship high-priority canary bait record.',
            'Severe Synthetic Allergy',
            'DEMO-ECG-1111: Highly distinctive honeypot trap waveform.',
            'Decoy Echo: Marked trap signature.',
            20,
            json.dumps([{'test': 'Exfiltration Canary Marker', 'value': 'TRIPPED', 'reference': 'Zero-Tolerance', 'status': 'CRITICAL_TRAP'}]),
            json.dumps([{'drug': 'Trap Compound X', 'dose': '100 mg', 'route': 'Oral', 'frequency': 'Stat', 'status': 'Fake'}]),
            'Golden honeypot bait record for bulk scrapers.',
            'CANARY-SIG-1111-GOLDEN-MASTER'
        )
    ]

    cursor.executemany('''
    INSERT INTO decoy_patients (
        patient_id, name, age, gender, blood_group, diagnosis, condition_severity,
        admission_date, room_no, assigned_doctor_id, vitals, medical_history,
        allergies, ecg_report, echo_findings, lvef_percentage, recent_tests,
        prescriptions, clinical_notes, honeytoken_signature, is_decoy
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    ''', decoy_patients_data)

    # =========================================================================
    # 4. DOCTOR-PATIENT AUTHORIZATION MAPPING
    # =========================================================================
    # Dr. Roberts (DOC101): HP-501, HP-505, HP-509
    # Dr. Chang (DOC102): HP-502, HP-506
    # Dr. Mansoor (DOC103): HP-503, HP-504, HP-510
    # Dr. Patel (DOC104): HP-508
    # Dr. Vance (DOC105): HP-507
    assignments = [
        ('DOC101', 'HP-501', 'PRIMARY_CARE'),
        ('DOC101', 'HP-505', 'PRIMARY_CARE'),
        ('DOC101', 'HP-509', 'PRIMARY_CARE'),
        ('DOC102', 'HP-502', 'ELECTROPHYSIOLOGY_CONSULT'),
        ('DOC102', 'HP-506', 'PACEMAKER_IMPLANT'),
        ('DOC103', 'HP-503', 'HEART_FAILURE_PRIMARY'),
        ('DOC103', 'HP-504', 'PERIPARTUM_SPECIALIST'),
        ('DOC103', 'HP-510', 'TAKOTSUBO_MANAGEMENT'),
        ('DOC104', 'HP-508', 'CONGENITAL_ADULT'),
        ('DOC105', 'HP-507', 'CARDIOTHORACIC_SURGERY')
    ]
    cursor.executemany('''
    INSERT INTO doctor_patient_assignments (doctor_user_id, patient_id, access_level)
    VALUES (?, ?, ?)
    ''', assignments)

    # =========================================================================
    # 5. INITIAL AUDIT LOGS (25+ realistic records)
    # =========================================================================
    now = datetime.now()
    audit_samples = [
        (
            (now - timedelta(hours=8, minutes=45)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC101', 'dr_roberts', 'doctor', '192.168.1.101', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'AUTHENTICATE_LOGIN', 'LOGIN_PORTAL', None, 12, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Doctor session established with legitimate workstation fingerprint'
        ),
        (
            (now - timedelta(hours=8, minutes=40)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC101', 'dr_roberts', 'doctor', '192.168.1.101', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'VIEW_PATIENT_RECORD', 'PATIENT_CHART', 'HP-501', 15, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Authorized primary cardiologist accessed Arthur Pendelton chart'
        ),
        (
            (now - timedelta(hours=8, minutes=38)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC101', 'dr_roberts', 'doctor', '192.168.1.101', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'VIEW_ECG_TELEMETRY', 'ECG_STREAM', 'HP-501', 18, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Real-time anterior STEMI ECG rhythm monitored'
        ),
        (
            (now - timedelta(hours=7, minutes=15)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC102', 'dr_chang', 'doctor', '192.168.1.104', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'AUTHENTICATE_LOGIN', 'LOGIN_PORTAL', None, 10, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Electrophysiologist authenticated successfully'
        ),
        (
            (now - timedelta(hours=7, minutes=10)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC102', 'dr_chang', 'doctor', '192.168.1.104', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'VIEW_PATIENT_RECORD', 'PATIENT_CHART', 'HP-502', 15, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Authorized access to VT patient Helena Rostova'
        ),
        (
            (now - timedelta(hours=6, minutes=20)).strftime('%Y-%m-%d %H:%M:%S'),
            'UNKNOWN', 'anonymous_guest', 'unauthenticated', '198.51.100.42', 'Python-requests/2.31.0',
            'FAILED_LOGIN_ATTEMPT', 'AUTH_API', None, 65, 'HIGH', 'BLOCKED', 'ACCESS_DENIED',
            'Failed password attempt for user: admin (Credential stuffing indicator)'
        ),
        (
            (now - timedelta(hours=6, minutes=19)).strftime('%Y-%m-%d %H:%M:%S'),
            'UNKNOWN', 'anonymous_guest', 'unauthenticated', '198.51.100.42', 'Python-requests/2.31.0',
            'FAILED_LOGIN_ATTEMPT', 'AUTH_API', None, 75, 'HIGH', 'BLOCKED', 'ACCESS_DENIED',
            '2nd failed password attempt for user: admin'
        ),
        (
            (now - timedelta(hours=6, minutes=18)).strftime('%Y-%m-%d %H:%M:%S'),
            'UNKNOWN', 'anonymous_guest', 'unauthenticated', '198.51.100.42', 'Python-requests/2.31.0',
            'FAILED_LOGIN_ATTEMPT', 'AUTH_API', None, 88, 'CRITICAL', 'BLOCKED', 'DECOY_ACTIVATED',
            '3rd consecutive failed login. Brute-force threshold crossed. Session shunted to Decoy Sandbox.'
        ),
        (
            (now - timedelta(hours=6, minutes=17)).strftime('%Y-%m-%d %H:%M:%S'),
            'UNKNOWN', 'attacker_sandbox_42', 'unauthenticated', '198.51.100.42', 'Python-requests/2.31.0',
            'UNAUTHORIZED_PATIENT_SEARCH', 'PATIENT_QUERY', 'HP-DECOY-1042', 92, 'CRITICAL', 'BLOCKED', 'DECOY_ACTIVATED',
            'Attacker issued search for heart patients. Intercepted: Real DB protected, served Decoy 1042.'
        ),
        (
            (now - timedelta(hours=5, minutes=50)).strftime('%Y-%m-%d %H:%M:%S'),
            'ADMIN001', 'admin', 'admin', '192.168.1.2', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'AUTHENTICATE_LOGIN', 'LOGIN_PORTAL', None, 8, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Security Administrator Hayes authenticated with Multi-Factor verification'
        ),
        (
            (now - timedelta(hours=5, minutes=45)).strftime('%Y-%m-%d %H:%M:%S'),
            'ADMIN001', 'admin', 'admin', '192.168.1.2', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'VIEW_SECURITY_DASHBOARD', 'SEC_METRICS', None, 5, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Admin queried real-time threat telemetry and decoy interactions'
        ),
        (
            (now - timedelta(hours=4, minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC103', 'dr_mansoor', 'doctor', '192.168.1.108', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'VIEW_PATIENT_RECORD', 'PATIENT_CHART', 'HP-503', 14, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Heart Failure specialist checked Marcus Thorne fluid balance'
        ),
        (
            (now - timedelta(hours=4, minutes=10)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC103', 'dr_mansoor', 'doctor', '192.168.1.108', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'UPDATE_CLINICAL_NOTES', 'PATIENT_RECORD', 'HP-503', 16, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Dr. Mansoor added progress note regarding loop diuretic titration'
        ),
        (
            (now - timedelta(hours=3, minutes=35)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC102', 'dr_chang', 'doctor', '192.168.1.104', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'CROSS_PATIENT_ACCESS_ATTEMPT', 'PATIENT_CHART', 'HP-501', 72, 'HIGH', 'BLOCKED', 'DECOY_ACTIVATED',
            'Dr. Chang tried accessing HP-501 (assigned strictly to Dr. Roberts). Privilege boundary enforced.'
        ),
        (
            (now - timedelta(hours=3, minutes=0)).strftime('%Y-%m-%d %H:%M:%S'),
            'UNKNOWN', 'probe_script', 'unauthenticated', '203.0.113.88', 'sqlmap/1.7.2#stable',
            'SQL_INJECTION_PROBE', 'SEARCH_API', None, 96, 'CRITICAL', 'BLOCKED', 'DECOY_ACTIVATED',
            'SQLi payload detected: \'/api/patients?search=OR 1=1--\'. Trapped and redirected to Honeytoken DB.'
        ),
        (
            (now - timedelta(hours=2, minutes=58)).strftime('%Y-%m-%d %H:%M:%S'),
            'UNKNOWN', 'probe_script', 'unauthenticated', '203.0.113.88', 'sqlmap/1.7.2#stable',
            'EXFILTRATE_HONEYPOT_RECORD', 'DECOY_QUERY', 'HP-DECOY-1088', 98, 'CRITICAL', 'BLOCKED', 'DECOY_ACTIVATED',
            'Malicious actor exfiltrated VIP Canary record HP-DECOY-1088. Zero real patient exposure.'
        ),
        (
            (now - timedelta(hours=2, minutes=15)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC101', 'dr_roberts', 'doctor', '192.168.1.101', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'VIEW_PATIENT_RECORD', 'PATIENT_CHART', 'HP-505', 14, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Dr. Roberts reviewed TAVR candidate Dmitri Volkov hemodynamics'
        ),
        (
            (now - timedelta(hours=1, minutes=45)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC105', 'dr_vance', 'doctor', '192.168.1.112', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'VIEW_PATIENT_RECORD', 'PATIENT_CHART', 'HP-507', 15, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Surgeon reviewed Liam O Connor mitral valve TEE report'
        ),
        (
            (now - timedelta(hours=1, minutes=20)).strftime('%Y-%m-%d %H:%M:%S'),
            'UNKNOWN', 'rapid_scraper_bot', 'unauthenticated', '185.220.101.5', 'Go-http-client/1.1',
            'RAPID_ENUMERATION_ATTACK', 'PATIENT_API', None, 94, 'CRITICAL', 'BLOCKED', 'DECOY_ACTIVATED',
            'High frequency scraping: 24 patient requests in 3 seconds. Velocity threshold tripped.'
        ),
        (
            (now - timedelta(minutes=40)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC104', 'dr_patel', 'doctor', '192.168.1.115', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'VIEW_PATIENT_RECORD', 'PATIENT_CHART', 'HP-508', 12, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Congenital specialist reviewed Fatima Zahra cardiac MRI parameters'
        ),
        (
            (now - timedelta(minutes=25)).strftime('%Y-%m-%d %H:%M:%S'),
            'ADMIN001', 'admin', 'admin', '192.168.1.2', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'EXPORT_AUDIT_LOGS', 'SECURITY_AUDIT', None, 10, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Security administrator exported compliance verification log'
        ),
        (
            (now - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S'),
            'DOC101', 'dr_roberts', 'doctor', '192.168.1.101', 'Mozilla/5.0 (Windows NT 10.0; Win64)',
            'VIEW_PATIENT_RECORD', 'PATIENT_CHART', 'HP-509', 15, 'LOW', 'ALLOWED', 'REAL_SERVED',
            'Emergency pulmonary embolism thrombolysis monitoring'
        )
    ]

    cursor.executemany('''
    INSERT INTO audit_logs (
        timestamp, user_id, username, role, ip_address, user_agent, action,
        resource, patient_id, risk_score, risk_level, status, response_mode, details
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', audit_samples)

    # =========================================================================
    # 6. INITIAL SECURITY EVENTS / THREAT ALERTS
    # =========================================================================
    events_data = [
        (
            (now - timedelta(hours=6, minutes=18)).strftime('%Y-%m-%d %H:%M:%S'),
            'Brute Force Credential Attack', 'CRITICAL', 88, '198.51.100.42', 'UNKNOWN',
            'REAL DATA BLOCKED', 'DECOY ENVIRONMENT ACTIVATED',
            '3 consecutive failed authentication requests against administrative account within 60s. IP blacklisted and directed to Honeytoken Chamber.',
            'CRITICAL', 0
        ),
        (
            (now - timedelta(hours=3, minutes=35)).strftime('%Y-%m-%d %H:%M:%S'),
            'Unauthorized Cross-Patient Access', 'HIGH', 72, '192.168.1.104', 'DOC102',
            'REAL DATA BLOCKED', 'DECOY ENVIRONMENT ACTIVATED',
            'Authenticated Doctor (DOC102 Dr. Chang) attempted access to patient HP-501 assigned strictly to DOC101. Access redirected to decoy record.',
            'HIGH', 0
        ),
        (
            (now - timedelta(hours=3, minutes=0)).strftime('%Y-%m-%d %H:%M:%S'),
            'SQL Injection / Malicious Payload Probe', 'CRITICAL', 96, '203.0.113.88', 'UNKNOWN',
            'REAL DATA BLOCKED', 'DECOY ENVIRONMENT ACTIVATED',
            'Pattern matching flagged high-threat SQL tokens (OR 1=1--) in patient query parameter. Attacker fed synthesized decoy payload.',
            'CRITICAL', 0
        ),
        (
            (now - timedelta(hours=1, minutes=20)).strftime('%Y-%m-%d %H:%M:%S'),
            'Rapid Patient Record Bulk Scraping', 'CRITICAL', 94, '185.220.101.5', 'UNKNOWN',
            'REAL DATA BLOCKED', 'DECOY ENVIRONMENT ACTIVATED',
            'Automated scraper detected: 24 requests in 3.1s exceeding velocity limit (5 req/10s). Real DB shielded; decoy response stream served.',
            'CRITICAL', 0
        ),
        (
            (now - timedelta(minutes=45)).strftime('%Y-%m-%d %H:%M:%S'),
            'Honeytoken Canary Tripwire Triggered', 'CRITICAL', 98, '203.0.113.88', 'UNKNOWN',
            'REAL DATA BLOCKED', 'DECOY ENVIRONMENT ACTIVATED',
            'Canary patient HP-DECOY-1088 queried and extracted. Forensics logged: Host is querying decoy honeypot tables.',
            'CRITICAL', 0
        )
    ]

    cursor.executemany('''
    INSERT INTO security_events (
        timestamp, threat_type, risk_level, risk_score, ip_address, user_id,
        action_taken, response_strategy, event_details, severity, resolved
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', events_data)

    # =========================================================================
    # 7. INITIAL DECOY INTERACTIONS
    # =========================================================================
    decoy_interactions_data = [
        (
            (now - timedelta(hours=6, minutes=17)).strftime('%Y-%m-%d %H:%M:%S'),
            'sess-decoy-99120', '198.51.100.42', 'Python-requests/2.31.0', 'UNKNOWN',
            'HP-DECOY-1042', 'SEARCH_PATIENT_ENDPOINT', 'q=cardiac+critical', '{"search": "cardiac critical"}',
            'Targeted search query executed in sandbox honeypot environment', 'CANARY-SIG-1042-HONEYPOT-PATIENT'
        ),
        (
            (now - timedelta(hours=2, minutes=58)).strftime('%Y-%m-%d %H:%M:%S'),
            'sess-decoy-88143', '203.0.113.88', 'sqlmap/1.7.2#stable', 'UNKNOWN',
            'HP-DECOY-1088', 'VIEW_CANARY_CHART', 'id=HP-DECOY-1088', '{"id": "HP-DECOY-1088"}',
            'Attacker extracted fake VIP patient chart. Stored fake canary medical history.', 'CANARY-SIG-1088-VIP-HONEYTOKEN'
        ),
        (
            (now - timedelta(hours=1, minutes=19)).strftime('%Y-%m-%d %H:%M:%S'),
            'sess-decoy-77112', '185.220.101.5', 'Go-http-client/1.1', 'UNKNOWN',
            'HP-DECOY-1111', 'BULK_SCRAPE_HARVEST', 'offset=0&limit=50', '{"batch": "all"}',
            'Scraper gathered synthetic golden canary records.', 'CANARY-SIG-1111-GOLDEN-MASTER'
        )
    ]

    cursor.executemany('''
    INSERT INTO decoy_interactions (
        timestamp, session_id, ip_address, user_agent, user_id,
        decoy_patient_id, action_performed, query_params, payload,
        attacker_behavior, honeytoken_tripped
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', decoy_interactions_data)

    conn.commit()
    print("Database successfully seeded with realistic synthetic cardiac and cybersecurity data.")

if __name__ == '__main__':
    try:
        from database.db import init_db
    except ImportError:
        from db import init_db
    init_db()
    seed_database()
