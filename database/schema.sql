-- =========================================================================
-- CYBER SECURITY & PRIVACY PROTECTION SYSTEM FOR CRITICAL HEART PATIENTS
-- SQLite Database Schema
-- =========================================================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL, -- 'admin', 'doctor', 'patient'
    name TEXT NOT NULL,
    email TEXT,
    status TEXT DEFAULT 'active', -- 'active', 'disabled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Doctors Table
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id TEXT UNIQUE NOT NULL, -- e.g. 'D001', 'D002'
    user_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    profile_photo TEXT DEFAULT NULL,
    specialty TEXT NOT NULL,
    specialization TEXT,
    qualification TEXT DEFAULT 'MBBS, MD Cardiology',
    experience TEXT DEFAULT '8 Years',
    department TEXT NOT NULL,
    email TEXT,
    demo_phone TEXT DEFAULT '+1 (555) 019-2834',
    permission_level TEXT NOT NULL DEFAULT 'NORMAL', -- 'NORMAL', 'CONFIDENTIAL', 'HIGHLY_CONFIDENTIAL'
    trusted_device_id TEXT,
    status TEXT DEFAULT 'active', -- 'active', 'disabled'
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 3. Protected Demo Patients Table (Real Synthetic Patients)
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT UNIQUE NOT NULL, -- e.g. 'HP001', 'HP002'
    user_id TEXT DEFAULT NULL,
    name TEXT NOT NULL,
    profile_photo TEXT DEFAULT NULL,
    age INTEGER NOT NULL,
    blood_group TEXT NOT NULL,
    gender TEXT NOT NULL,
    assigned_doctor_id TEXT NOT NULL,
    heart_condition_category TEXT NOT NULL, -- 'STEMI', 'Ventricular Tachycardia', 'Heart Failure', etc.
    medical_history TEXT NOT NULL,
    ecg_report TEXT NOT NULL,
    echo_report TEXT NOT NULL,
    blood_test_report TEXT NOT NULL,
    current_prescriptions TEXT NOT NULL,
    email TEXT DEFAULT NULL,
    phone_number TEXT DEFAULT '+1 (555) 019-1001',
    emergency_contact TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_sensitivity_level TEXT NOT NULL DEFAULT 'NORMAL', -- 'NORMAL', 'CONFIDENTIAL', 'HIGHLY_CONFIDENTIAL'
    vitals TEXT NOT NULL,
    status TEXT DEFAULT 'active', -- 'active', 'disabled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_decoy INTEGER DEFAULT 0
);

-- 4. Doctor-Patient Assignments
CREATE TABLE IF NOT EXISTS doctor_patient_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'ACTIVE',
    UNIQUE(doctor_id, patient_id)
);

-- 5. Medical Records Table
CREATE TABLE IF NOT EXISTS medical_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    record_type TEXT NOT NULL, -- 'PROGRESS_NOTE', 'SURGERY', 'CATH_LAB', 'MEDICATION_CHANGE'
    clinical_notes TEXT NOT NULL,
    recorded_by_doctor_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

-- 6. Confidential Records Table
CREATE TABLE IF NOT EXISTS confidential_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL,
    sensitivity_level TEXT NOT NULL, -- 'CONFIDENTIAL', 'HIGHLY_CONFIDENTIAL'
    title TEXT NOT NULL,
    confidential_notes TEXT NOT NULL,
    required_permission TEXT NOT NULL, -- 'CONFIDENTIAL', 'HIGHLY_CONFIDENTIAL'
    restricted_reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
);

-- 7. Emergency Break-Glass Access Records
CREATE TABLE IF NOT EXISTS emergency_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    risk_score_before INTEGER NOT NULL,
    risk_score_after INTEGER NOT NULL,
    approved INTEGER DEFAULT 1,
    status TEXT DEFAULT 'ACTIVE' -- 'ACTIVE', 'EXPIRED', 'REVOKED'
);

-- 8. Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    device_id TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- 9. Risk Scores Table
CREATE TABLE IF NOT EXISTS risk_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    current_score INTEGER NOT NULL DEFAULT 10,
    risk_level TEXT NOT NULL DEFAULT 'LOW',
    last_evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, session_id)
);

-- 10. Risk Events Table
CREATE TABLE IF NOT EXISTS risk_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    session_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    factor_name TEXT NOT NULL,
    score_delta INTEGER NOT NULL,
    new_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    description TEXT NOT NULL
);

-- 11. Security Alerts Table
CREATE TABLE IF NOT EXISTS security_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT UNIQUE NOT NULL,
    threat_type TEXT NOT NULL,
    severity TEXT NOT NULL, -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    user_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    risk_score INTEGER NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'NEW' -- 'NEW', 'INVESTIGATING', 'RESOLVED'
);

-- 12. Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    patient_id TEXT,
    action TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    device_status TEXT NOT NULL, -- 'TRUSTED', 'UNKNOWN'
    risk_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    result TEXT NOT NULL, -- 'SUCCESS', 'DENIED', 'DECOY_SERVED', 'FLAGGED'
    threat_type TEXT,
    session_id TEXT,
    details TEXT
);

-- 13. Decoy / Honeypot Patients Table (Isolated Fake Records)
CREATE TABLE IF NOT EXISTS decoy_patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT UNIQUE NOT NULL, -- e.g. 'HP-DEC-101'..'HP-DEC-112'
    name TEXT NOT NULL,
    profile_photo TEXT DEFAULT NULL,
    age INTEGER NOT NULL,
    blood_group TEXT NOT NULL,
    gender TEXT NOT NULL,
    assigned_doctor TEXT NOT NULL,
    heart_condition_category TEXT NOT NULL,
    medical_history TEXT NOT NULL,
    ecg_report TEXT NOT NULL,
    echo_report TEXT NOT NULL,
    blood_test_report TEXT NOT NULL,
    current_prescriptions TEXT NOT NULL,
    phone_number TEXT DEFAULT '+1 (555) 019-9999',
    emergency_contact TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_sensitivity_level TEXT DEFAULT 'NORMAL',
    vitals TEXT NOT NULL,
    honeytoken_tag TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    is_decoy INTEGER DEFAULT 1
);

-- 14. Decoy Medical Records Table
CREATE TABLE IF NOT EXISTS decoy_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decoy_patient_id TEXT NOT NULL,
    fake_diagnosis TEXT NOT NULL,
    fake_clinical_notes TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Decoy Sessions / Trapped Interaction Table
CREATE TABLE IF NOT EXISTS decoy_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decoy_session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fake_patient_searched TEXT,
    fake_record_viewed TEXT,
    actions_performed TEXT NOT NULL,
    request_count INTEGER DEFAULT 1,
    risk_score INTEGER NOT NULL,
    threat_level TEXT NOT NULL
);

-- 16. Device Status Table
CREATE TABLE IF NOT EXISTS device_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    device_name TEXT NOT NULL,
    device_status TEXT NOT NULL DEFAULT 'TRUSTED', -- 'TRUSTED', 'UNKNOWN'
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    risk_contribution INTEGER NOT NULL -- -5 for TRUSTED, +20 for UNKNOWN
);

-- 17. Failed Login Attempts Tracker
CREATE TABLE IF NOT EXISTS failed_logins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    username_attempted TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
