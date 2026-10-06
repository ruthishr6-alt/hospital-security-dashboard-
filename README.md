# Critical Heart Patient Cyber Security System 🛡️❤️

> **Academic / Cybersecurity Prototype Only**  
> **DISCLAIMER:** This application is strictly an academic cybersecurity prototype. All patient records, ECG traces, Echo values, blood test reports, prescriptions, and clinician credentials are **100% synthetic demo data**. This system does not contain protected health information (PHI) and must not be used for actual clinical medical diagnosis or treatment.

---

## 📌 Executive Summary

The **Critical Heart Patient Cyber Security System** is a full-stack cybersecurity healthcare web platform specifically built to protect critical heart patients from modern cyber threats, unauthorized data access, credential stuffing, and medical record exfiltration.

The system combines:
1. **Dynamic Risk-Based Access Control (Risk Engine)**: Computes a multi-factor risk score (0–100) for every sensitive clinical request.
2. **Autonomous Threat Detection Engine**: Detects brute-force attacks, scraping bots, cross-patient privilege violations, and malicious injection payloads in real time.
3. **Decoy Medical Records & Isolated Honeypot Subsystem**: When suspicious activity or critical risk is detected, the system **never exposes real records**; instead, it seamlessly traps the attacker inside an isolated honeypot environment populated by synthetic canary records.
4. **Tamper-Evident Audit Trail**: Cryptographically logs every allowed, blocked, and deceptive event.
5. **Interactive Security Operations Center (SOC) Dashboard**: Real-time telemetry, 10 executive metric cards, 7 dynamic Chart.js visualizations, and an embedded **Cyber Attack Demonstration Center** with 6 attack scenarios.
6. **Cardiologist Clinical Station**: Complete critical care cardiac chart with a **real-time HTML5 Canvas ECG Rhythm Waveform Visualizer** (sinus rhythm, anterior STEMI, ventricular tachycardia).
7. **Doctor & Patient Profile Photo System**: Complete profile photo subsystem with upload, change, removal, 5MB ceiling, magic bytes security checking, and SVG avatar fallbacks.

---

## 👥 User Roles & Demo Credentials

| Role | Username | Password | Doctor ID | Assigned Patients | Clearance Tier |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Security Admin** | `admin_demo` | `AdminDemo#2026!` | N/A | Executive SOC Access | **ADMIN / FULL** |
| **Cardiologist 1 (Lead)** | `doctor_demo_01` | `DoctorDemo#2026!` | `D001` (Dr. Sarah Lin) | `HP001`, `HP002`, `HP010` | `HIGHLY_CONFIDENTIAL` |
| **Cardiologist 2** | `doctor_demo_02` | `DoctorDemo#2026!` | `D002` (Dr. Marcus Vance) | `HP003`, `HP004` | `CONFIDENTIAL` |
| **Cardiologist 3** | `doctor_demo_03` | `DoctorDemo#2026!` | `D003` (Dr. Elena Rostova)| `HP005`, `HP006` | `NORMAL` |
| **Cardiologist 4** | `doctor_demo_04` | `DoctorDemo#2026!` | `D004` (Dr. David Kim) | `HP007`, `HP008` | `NORMAL` |
| **Cardiologist 5** | `doctor_demo_05` | `DoctorDemo#2026!` | `D005` (Dr. Maya Patel) | `HP009`, `HP011`, `HP012` | `CONFIDENTIAL` |
| **Attacker / Unauthorized**| *(Anonymous / Guest)* | *(Invalid)* | N/A | Probes trigger Honeypot | **UNTRUSTED / DECOY TRAP** |

*Fast login and 1-click role switcher buttons are available directly on the login portal and via `/api/auth/demo-switch/<username>`.*

---

## 🧮 Risk-Based Access Control (Risk Engine)

Every sensitive request is evaluated by `services/risk_engine.py` against 7 core security heuristics:

$$\text{Risk Score} = \min(100, \max(0, 25 + \sum \text{Factors}))$$

### Risk Levels & Defensive Actions:
- **0–30 = LOW**: Normal authorized clinician workflow $\rightarrow$ **Allow real synthetic patient data**.
- **31–60 = MEDIUM**: Minor velocity fluctuation or first login from device $\rightarrow$ **Allow with heightened logging**.
- **61–80 = HIGH**: Doctor attempting unassigned patient $\rightarrow$ **Access Denied & Security Alert generated**.
- **81–100 = CRITICAL**: Brute force, rapid scraping bot, SQLi, or canary probe $\rightarrow$ **Block real database, activate Decoy Honeypot, alert Security Admin**.

---

## 🎭 Decoy / Honeypot Deception System

- **Physically Isolated Tables**: Real protected demo data lives in `patients`, while decoy honeytokens live exclusively in `decoy_patients`.
- **Canary Bait Records**:
  - `HP-DEC-101`: Demo Patient 1042 (*Canary Trap #01*)
  - `HP-DEC-102`: Demo Patient 1088 (*VIP High-Attraction Honeytoken*)
  - `HP-DEC-103`: Demo Patient 1099 (*Post-Resuscitation Canary*)
  - `HP-DEC-104`: Demo Patient 1100 (*SQLi Trap Node*)
  - `HP-DEC-105`: Demo Patient 1105 (*Behavioral Entrapment Node*)
  - `HP-DEC-106`: Demo Patient 1111 (*Golden Master Canary Bait*)
  - `HP-DEC-107`: Demo Patient 1115 (*Shadow Canary Sandbox*)
  - `HP-DEC-108`: Demo Patient 1120 (*Scraper Trap Canary*)
  - `HP-DEC-109`: Demo Patient 1125 (*Telemetry Decoy Lure*)
  - `HP-DEC-110`: Demo Patient 1130 (*Exfiltration Tripwire Canary*)
- **Adversary Forensics**:
  When attackers enter the decoy chamber, the system logs their IP address, fake patient searched, query parameters, executed payloads, and timestamp into `decoy_sessions`.

---

## 📸 Doctor & Patient Profile Photo System

A cryptographically secure profile photo subsystem is built across both Doctor and Patient entities:
- **Doctor Profiles**: Specialization, Qualification, Experience, Department, Demo Phone, Account Status, and circular photo component with `DOCTOR` badge.
- **Patient Profiles**: Heart Condition Category, Blood Group, Age, Gender, Sensitivity Tier, and circular photo component with `PATIENT – DEMO` badge.
- **Photo Security**:
  - Whitelisted extensions only: `.jpg`, `.jpeg`, `.png`, `.webp`
  - Magic bytes binary verification (JPEG, PNG, WEBP)
  - 5MB maximum file size ceiling
  - Cryptographically randomized UUID filenames preventing path traversal
  - Dedicated isolated upload directories (`static/uploads/doctors`, `static/uploads/patients`, `static/uploads/decoys`)
  - Automatic fallback to high-resolution vector SVG avatars (`doctor_default.svg`, `patient_default.svg`, `decoy_default.svg`)
- **Admin Management**: Admins can upload, replace, remove photos, and toggle account statuses in Doctor Management (`/admin/users`) and Patient Management (`/admin/patients`).

---

## 🛠️ Project Structure

```
project/
├── app.py                     # Flask application factory, routes, headers, context
├── python.bat                 # Workspace Python launcher wrapper
├── run.bat                    # Windows 1-click startup script
├── run.ps1                    # PowerShell startup script
├── requirements.txt           # Python dependencies
├── test_app.py                # 30-step automated verification suite
├── database/
│   ├── db.py                  # SQLite connection and schema initializer
│   ├── schema.sql             # Relational database schema with constraints
│   ├── seed.py                # Synthetic demo data seeder (doctors, patients, decoys)
│   └── database.db            # SQLite database
├── models/
│   ├── user.py                # Clinician, admin, and doctor models
│   ├── patient.py             # Cardiac patient and sensitivity models
│   └── record.py              # Medical records and emergency access models
├── routes/
│   ├── auth.py                # Login, MFA verification, profile, logout
│   ├── doctor.py              # Clinical ward, records, confidential vault, emergency access
│   ├── patients.py            # Patient list, search, and detailed chart
│   ├── admin.py               # SOC dashboard, doctor management, patient management, assignments
│   ├── security.py            # Threat monitor, alerts, audit logs, devices, 6-scenario simulator
│   └── decoy.py               # Isolated honeypot sandbox and canary endpoints
├── services/
│   ├── risk_engine.py         # Dynamic 0-100 Risk Engine with 7 heuristics
│   ├── threat_detector.py     # Intrusion and anomaly detection engine
│   ├── deception_service.py   # Honeypot decoy management and canary forensics
│   ├── audit_service.py       # Tamper-evident audit logging
│   └── photo_service.py       # Secure photo upload, magic byte check, and SVG avatar fallback
├── templates/
│   ├── base.html              # Cyber navigation, live threat pill, and doctor avatar
│   ├── login.html             # Multi-factor authentication portal with 1-click test cards
│   ├── mfa.html               # 6-digit OTP verification view
│   ├── profile.html           # Doctor security profile with large photo and assigned patients
│   ├── doctor_dashboard.html  # Clinical Cardiology Station with vitals and patient table
│   ├── patient_list.html      # Filterable inpatient cardiac directory with photos & badges
│   ├── patient_detail.html    # Detailed chart with large photo and real-time Canvas ECG
│   ├── medical_records.html   # Clinical progress notes archive with patient thumbnails
│   ├── confidential_records.html # 3-tier restricted clinical dossiers vault
│   ├── emergency_access.html  # 15-minute emergency break-glass override protocol
│   ├── admin_dashboard.html   # SOC Dashboard with 10 cards, 7 charts, doctor & patient panels
│   ├── user_management.html   # Doctor account and profile photo management
│   ├── admin_patients.html    # Synthetic cardiac patient and photo management
│   ├── doctor_patient_assignment.html # Doctor-patient authorization matrix
│   ├── threat_monitor.html    # IDS heuristics & threat classification feed
│   ├── security_alerts.html   # Live security incident alerts & resolution
│   ├── decoy_monitor.html     # Honeypot telemetry console & trapped attacker sessions
│   ├── decoy.html             # Isolated honeypot catalog with synthetic decoy photos
│   ├── audit_logs.html        # Tamper-evident forensic audit logs with multi-filters
│   ├── device_security.html   # Zero-Trust hardware terminal binding console
│   └── risk_analysis.html     # Dynamic risk score breakdown & 6-scenario simulator
└── static/
    ├── css/
    │   └── style.css          # Dark medical-cybersecurity stylesheet
    ├── js/
    │   ├── main.js            # Frontend utility scripts & role switcher
    │   ├── ecg_visualizer.js  # Real-time HTML5 Canvas ECG waveform animator
    │   ├── charts.js          # Chart.js analytics renderer (7 telemetry streams)
    │   └── simulator.js       # Interactive Attack Simulator controller
    ├── img/
    │   └── avatars/           # Professional default SVG avatars (doctor, patient, decoy)
    └── uploads/               # Photo upload directories (doctors, patients, decoys)
```

---

## 🚀 Installation & How to Run

### Option 1: Double-Click (Windows)
Double-click `run.bat` in the project folder.

### Option 2: PowerShell / Terminal
```powershell
# From the project directory:
.\run.bat
# Or using the local python wrapper:
.\python.bat app.py
```

### Option 3: Run Full Automated Verification Suite (30 Tests)
```powershell
.\python.bat test_app.py
```

### Accessing the Web Application
Open your web browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

---

## 🎨 UI/UX Specifications
- **Theme**: Dark medical-cybersecurity theme.
- **Palette**:
  - Deep Space Navy: `#060913`, `#0b1120`, `#0f172a`
  - Neon Medical Cyan: `#00e5ff`
  - Cardiac Crimson / Threat Alert: `#ff1744`
  - Safe Emerald: `#00e676`
  - Caution Amber: `#ffb300`
  - Decoy Purple: `#c084fc`
- **Canvas Waveform**: Real-time Lead II cardiac rhythm simulation rendering continuous P-Q-R-S-T complexes with customizable sweep speed and clinical patterns.
- **Badges**:
  - Clinicians: `DOCTOR` (Cyan)
  - Patients: `PATIENT – DEMO` (Crimson)
  - Honeypot Decoys: `SYNTHETIC DECOY DATA` (Purple)
