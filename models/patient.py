import json
from datetime import datetime
from database.db import query_db, execute_db

class PatientModel:
    @staticmethod
    def get_all():
        rows = query_db("SELECT * FROM patients ORDER BY patient_id ASC")
        return [PatientModel._format(r) for r in rows]

    @staticmethod
    def get_by_id(patient_id):
        row = query_db('''
            SELECT p.*, d.name AS assigned_doctor_name, d.specialization AS assigned_doctor_specialty
            FROM patients p
            LEFT JOIN doctors d ON p.assigned_doctor_id = d.doctor_id
            WHERE p.patient_id = ?
        ''', (patient_id,), one=True)
        return PatientModel._format(row) if row else None

    @staticmethod
    def get_assigned_to_doctor(doctor_id):
        rows = query_db('''
            SELECT p.*
            FROM patients p
            JOIN doctor_patient_assignments a ON p.patient_id = a.patient_id
            WHERE a.doctor_id = ? AND a.status = 'ACTIVE'
            ORDER BY p.patient_id ASC
        ''', (doctor_id,))
        return [PatientModel._format(r) for r in rows]

    @staticmethod
    def is_assigned(doctor_id, patient_id):
        row = query_db('''
            SELECT id FROM doctor_patient_assignments
            WHERE doctor_id = ? AND patient_id = ? AND status = 'ACTIVE'
        ''', (doctor_id, patient_id), one=True)
        return bool(row)

    @staticmethod
    def has_emergency_access(doctor_id, patient_id):
        """Checks if a valid, non-expired emergency break-glass grant exists."""
        row = query_db('''
            SELECT * FROM emergency_access
            WHERE doctor_id = ? AND patient_id = ? AND status = 'ACTIVE'
              AND expires_at > CURRENT_TIMESTAMP
            ORDER BY id DESC LIMIT 1
        ''', (doctor_id, patient_id), one=True)
        return bool(row)

    @staticmethod
    def get_emergency_grant(doctor_id, patient_id):
        return query_db('''
            SELECT * FROM emergency_access
            WHERE doctor_id = ? AND patient_id = ? AND status = 'ACTIVE'
              AND expires_at > CURRENT_TIMESTAMP
            ORDER BY id DESC LIMIT 1
        ''', (doctor_id, patient_id), one=True)

    @staticmethod
    def can_access_sensitivity(doctor_permission, record_sensitivity):
        """
        Sensitivity hierarchy:
        - NORMAL: accessible by NORMAL, CONFIDENTIAL, HIGHLY_CONFIDENTIAL
        - CONFIDENTIAL: accessible by CONFIDENTIAL, HIGHLY_CONFIDENTIAL
        - HIGHLY_CONFIDENTIAL: accessible only by HIGHLY_CONFIDENTIAL
        """
        hierarchy = {'NORMAL': 1, 'CONFIDENTIAL': 2, 'HIGHLY_CONFIDENTIAL': 3}
        doc_rank = hierarchy.get(doctor_permission, 1)
        rec_rank = hierarchy.get(record_sensitivity, 1)
        return doc_rank >= rec_rank

    @staticmethod
    def search(query_str, doctor_id=None):
        wildcard = f"%{query_str}%"
        if doctor_id:
            rows = query_db('''
                SELECT p.* FROM patients p
                JOIN doctor_patient_assignments a ON p.patient_id = a.patient_id
                WHERE a.doctor_id = ? AND a.status = 'ACTIVE'
                  AND (p.name LIKE ? OR p.patient_id LIKE ? OR p.heart_condition_category LIKE ?)
                ORDER BY p.patient_id ASC
            ''', (doctor_id, wildcard, wildcard, wildcard))
        else:
            rows = query_db('''
                SELECT * FROM patients
                WHERE name LIKE ? OR patient_id LIKE ? OR heart_condition_category LIKE ?
                ORDER BY patient_id ASC
            ''', (wildcard, wildcard, wildcard))
        return [PatientModel._format(r) for r in rows]

    @staticmethod
    def update_clinical_notes(patient_id, notes, doctor_id):
        execute_db('''
            INSERT INTO medical_records (patient_id, record_type, clinical_notes, recorded_by_doctor_id)
            VALUES (?, 'PROGRESS_NOTE', ?, ?)
        ''', (patient_id, notes, doctor_id))
        execute_db('''
            UPDATE patients SET last_updated = CURRENT_TIMESTAMP WHERE patient_id = ?
        ''', (patient_id,))

    @staticmethod
    def get_by_user_id(user_id):
        row = query_db('''
            SELECT p.*, d.name AS assigned_doctor_name, d.specialization AS assigned_doctor_specialty
            FROM patients p
            LEFT JOIN doctors d ON p.assigned_doctor_id = d.doctor_id
            WHERE p.user_id = ?
        ''', (user_id,), one=True)
        return PatientModel._format(row) if row else None

    @staticmethod
    def generate_unique_patient_id():
        rows = query_db("SELECT patient_id FROM patients")
        nums = []
        for r in rows:
            pid = r['patient_id']
            if pid and pid.startswith('HP') and not pid.startswith('HP-DEC'):
                try:
                    num_part = int(pid.replace('HP', ''))
                    nums.append(num_part)
                except ValueError:
                    pass
        next_num = (max(nums) + 1) if nums else 1
        candidate = f"HP{next_num:03d}"
        while query_db("SELECT id FROM patients WHERE patient_id = ?", (candidate,), one=True):
            next_num += 1
            candidate = f"HP{next_num:03d}"
        return candidate

    @staticmethod
    def create_patient(patient_id, name, age, blood_group, gender, assigned_doctor_id,
                       heart_condition_category, medical_history, ecg_report, echo_report,
                       blood_test_report, current_prescriptions, emergency_contact,
                       record_sensitivity_level='NORMAL', vitals='HR: 75 bpm | BP: 120/80 mmHg | SpO2: 98%',
                       profile_photo=None, status='active', phone_number='+1 (555) 019-1001',
                       user_id=None, email=None):
        execute_db('''
            INSERT INTO patients (
                patient_id, user_id, name, profile_photo, age, blood_group, gender, assigned_doctor_id,
                heart_condition_category, medical_history, ecg_report, echo_report,
                blood_test_report, current_prescriptions, email, phone_number, emergency_contact,
                record_sensitivity_level, vitals, status, is_decoy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (
            patient_id, user_id, name, profile_photo, age, blood_group, gender, assigned_doctor_id,
            heart_condition_category, medical_history, ecg_report, echo_report,
            blood_test_report, current_prescriptions, email, phone_number, emergency_contact,
            record_sensitivity_level, vitals, status
        ))
        # Also create initial assignment
        if assigned_doctor_id:
            execute_db('''
                INSERT INTO doctor_patient_assignments (doctor_id, patient_id, status)
                VALUES (?, ?, 'ACTIVE')
                ON CONFLICT(doctor_id, patient_id) DO UPDATE SET status = 'ACTIVE'
            ''', (assigned_doctor_id, patient_id))

    @staticmethod
    def update_own_patient_profile(patient_id, name, phone_number, email, emergency_contact,
                                   heart_condition_category, medical_history,
                                   age=None, gender=None, blood_group=None, profile_photo=None):
        if profile_photo:
            execute_db('''
                UPDATE patients
                SET name = ?, phone_number = ?, email = ?, emergency_contact = ?,
                    heart_condition_category = ?, medical_history = ?,
                    age = coalesce(?, age), gender = coalesce(?, gender),
                    blood_group = coalesce(?, blood_group), profile_photo = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE patient_id = ?
            ''', (name, phone_number, email, emergency_contact, heart_condition_category,
                  medical_history, age, gender, blood_group, profile_photo, patient_id))
        else:
            execute_db('''
                UPDATE patients
                SET name = ?, phone_number = ?, email = ?, emergency_contact = ?,
                    heart_condition_category = ?, medical_history = ?,
                    age = coalesce(?, age), gender = coalesce(?, gender),
                    blood_group = coalesce(?, blood_group),
                    last_updated = CURRENT_TIMESTAMP
                WHERE patient_id = ?
            ''', (name, phone_number, email, emergency_contact, heart_condition_category,
                  medical_history, age, gender, blood_group, patient_id))

        pat = query_db("SELECT user_id FROM patients WHERE patient_id = ?", (patient_id,), one=True)
        if pat and pat['user_id']:
            execute_db("UPDATE users SET name = ?, email = coalesce(?, email) WHERE user_id = ?", (name, email, pat['user_id']))

    @staticmethod
    def update_patient(patient_id, name, age, blood_group, gender, assigned_doctor_id,
                       heart_condition_category, medical_history, ecg_report, echo_report,
                       blood_test_report, current_prescriptions, emergency_contact,
                       record_sensitivity_level, status='active', profile_photo=None,
                       phone_number=None):
        if profile_photo and phone_number:
            execute_db('''
                UPDATE patients
                SET name = ?, profile_photo = ?, age = ?, blood_group = ?, gender = ?,
                    assigned_doctor_id = ?, heart_condition_category = ?, medical_history = ?,
                    ecg_report = ?, echo_report = ?, blood_test_report = ?,
                    current_prescriptions = ?, phone_number = ?, emergency_contact = ?,
                    record_sensitivity_level = ?, status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE patient_id = ?
            ''', (
                name, profile_photo, age, blood_group, gender, assigned_doctor_id,
                heart_condition_category, medical_history, ecg_report, echo_report,
                blood_test_report, current_prescriptions, phone_number, emergency_contact,
                record_sensitivity_level, status, patient_id
            ))
        elif profile_photo:
            execute_db('''
                UPDATE patients
                SET name = ?, profile_photo = ?, age = ?, blood_group = ?, gender = ?,
                    assigned_doctor_id = ?, heart_condition_category = ?, medical_history = ?,
                    ecg_report = ?, echo_report = ?, blood_test_report = ?,
                    current_prescriptions = ?, emergency_contact = ?,
                    record_sensitivity_level = ?, status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE patient_id = ?
            ''', (
                name, profile_photo, age, blood_group, gender, assigned_doctor_id,
                heart_condition_category, medical_history, ecg_report, echo_report,
                blood_test_report, current_prescriptions, emergency_contact,
                record_sensitivity_level, status, patient_id
            ))
        elif phone_number:
            execute_db('''
                UPDATE patients
                SET name = ?, age = ?, blood_group = ?, gender = ?,
                    assigned_doctor_id = ?, heart_condition_category = ?, medical_history = ?,
                    ecg_report = ?, echo_report = ?, blood_test_report = ?,
                    current_prescriptions = ?, phone_number = ?, emergency_contact = ?,
                    record_sensitivity_level = ?, status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE patient_id = ?
            ''', (
                name, age, blood_group, gender, assigned_doctor_id,
                heart_condition_category, medical_history, ecg_report, echo_report,
                blood_test_report, current_prescriptions, phone_number, emergency_contact,
                record_sensitivity_level, status, patient_id
            ))
        else:
            execute_db('''
                UPDATE patients
                SET name = ?, age = ?, blood_group = ?, gender = ?,
                    assigned_doctor_id = ?, heart_condition_category = ?, medical_history = ?,
                    ecg_report = ?, echo_report = ?, blood_test_report = ?,
                    current_prescriptions = ?, emergency_contact = ?,
                    record_sensitivity_level = ?, status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE patient_id = ?
            ''', (
                name, age, blood_group, gender, assigned_doctor_id,
                heart_condition_category, medical_history, ecg_report, echo_report,
                blood_test_report, current_prescriptions, emergency_contact,
                record_sensitivity_level, status, patient_id
            ))

        # Update assignment if doctor changed
        if assigned_doctor_id:
            execute_db('''
                INSERT INTO doctor_patient_assignments (doctor_id, patient_id, status)
                VALUES (?, ?, 'ACTIVE')
                ON CONFLICT(doctor_id, patient_id) DO UPDATE SET status = 'ACTIVE'
            ''', (assigned_doctor_id, patient_id))

    @staticmethod
    def remove_patient_photo(patient_id):
        execute_db("UPDATE patients SET profile_photo = NULL WHERE patient_id = ?", (patient_id,))

    @staticmethod
    def set_patient_status(patient_id, status):
        execute_db("UPDATE patients SET status = ?, last_updated = CURRENT_TIMESTAMP WHERE patient_id = ?", (status, patient_id))

    @staticmethod
    def assign_doctor(doctor_id, patient_id):
        execute_db('''
            INSERT INTO doctor_patient_assignments (doctor_id, patient_id, status)
            VALUES (?, ?, 'ACTIVE')
            ON CONFLICT(doctor_id, patient_id) DO UPDATE SET status = 'ACTIVE'
        ''', (doctor_id, patient_id))
        execute_db("UPDATE patients SET assigned_doctor_id = ? WHERE patient_id = ?", (doctor_id, patient_id))

    @staticmethod
    def delete_patient(patient_id):
        pat = query_db("SELECT user_id, name FROM patients WHERE patient_id = ?", (patient_id,), one=True)
        if pat:
            execute_db("DELETE FROM doctor_patient_assignments WHERE patient_id = ?", (patient_id,))
            execute_db("DELETE FROM medical_records WHERE patient_id = ?", (patient_id,))
            execute_db("DELETE FROM emergency_access WHERE patient_id = ?", (patient_id,))
            execute_db("DELETE FROM patients WHERE patient_id = ?", (patient_id,))
            if pat['user_id']:
                execute_db("DELETE FROM users WHERE user_id = ?", (pat['user_id'],))
            return pat
        return None

    @staticmethod
    def _format(row):
        if not row:
            return None
        d = dict(row)
        for key in ['vitals', 'current_prescriptions']:
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        d['is_decoy'] = d.get('is_decoy', 0)
        return d
