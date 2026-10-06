from database.db import query_db, execute_db

class RecordModel:
    @staticmethod
    def get_medical_records_by_patient(patient_id):
        return query_db('''
            SELECT m.*, d.name as doctor_name, d.profile_photo as doctor_photo, p.profile_photo as patient_photo
            FROM medical_records m
            JOIN patients p ON m.patient_id = p.patient_id
            LEFT JOIN doctors d ON m.recorded_by_doctor_id = d.doctor_id
            WHERE m.patient_id = ?
            ORDER BY m.created_at DESC
        ''', (patient_id,))

    @staticmethod
    def get_all_medical_records():
        return query_db('''
            SELECT m.*, p.name as patient_name, p.profile_photo as patient_photo, d.name as doctor_name, d.profile_photo as doctor_photo
            FROM medical_records m
            JOIN patients p ON m.patient_id = p.patient_id
            LEFT JOIN doctors d ON m.recorded_by_doctor_id = d.doctor_id
            ORDER BY m.created_at DESC
        ''')

    @staticmethod
    def get_confidential_records_by_patient(patient_id):
        return query_db('''
            SELECT c.*, p.name as patient_name, p.profile_photo as patient_photo
            FROM confidential_records c
            JOIN patients p ON c.patient_id = p.patient_id
            WHERE c.patient_id = ?
            ORDER BY c.created_at DESC
        ''', (patient_id,))

    @staticmethod
    def get_all_confidential_records():
        return query_db('''
            SELECT c.*, p.name as patient_name, p.profile_photo as patient_photo, p.assigned_doctor_id
            FROM confidential_records c
            JOIN patients p ON c.patient_id = p.patient_id
            ORDER BY c.sensitivity_level DESC, c.created_at DESC
        ''')

    @staticmethod
    def create_emergency_access(doctor_id, patient_id, session_id, reason, expires_at, risk_before, risk_after):
        return execute_db('''
            INSERT INTO emergency_access (
                doctor_id, patient_id, session_id, reason, expires_at,
                risk_score_before, risk_score_after, approved, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'ACTIVE')
        ''', (doctor_id, patient_id, session_id, reason, expires_at, risk_before, risk_after))

    @staticmethod
    def get_all_emergency_access():
        return query_db('''
            SELECT e.*, d.name as doctor_name, d.profile_photo as doctor_photo, p.name as patient_name, p.profile_photo as patient_photo,
                   CASE WHEN e.expires_at > CURRENT_TIMESTAMP AND e.status = 'ACTIVE' THEN 1 ELSE 0 END as is_active
            FROM emergency_access e
            JOIN doctors d ON e.doctor_id = d.doctor_id
            JOIN patients p ON e.patient_id = p.patient_id
            ORDER BY e.requested_at DESC
        ''')
