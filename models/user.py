from database.db import query_db, execute_db

class UserModel:
    @staticmethod
    def get_by_username(username):
        return query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)

    @staticmethod
    def get_by_user_id(user_id):
        return query_db("SELECT * FROM users WHERE user_id = ?", (user_id,), one=True)

    @staticmethod
    def get_doctor_by_user_id(user_id):
        return query_db("SELECT * FROM doctors WHERE user_id = ?", (user_id,), one=True)

    @staticmethod
    def get_doctor_by_doctor_id(doctor_id):
        return query_db('''
            SELECT d.*, u.username, u.email as user_email, u.status as user_status
            FROM doctors d
            JOIN users u ON d.user_id = u.user_id
            WHERE d.doctor_id = ?
        ''', (doctor_id,), one=True)

    @staticmethod
    def get_all_doctors():
        return query_db('''
            SELECT d.*, u.username, u.email as user_email, u.status as user_status
            FROM doctors d
            JOIN users u ON d.user_id = u.user_id
            ORDER BY d.doctor_id ASC
        ''')

    @staticmethod
    def get_all_users():
        return query_db("SELECT * FROM users ORDER BY role, username")

    @staticmethod
    def update_doctor_permissions(doctor_id, permission_level, status):
        execute_db('''
            UPDATE doctors
            SET permission_level = ?, status = ?
            WHERE doctor_id = ?
        ''', (permission_level, status, doctor_id))
        doc = query_db("SELECT user_id FROM doctors WHERE doctor_id = ?", (doctor_id,), one=True)
        if doc:
            execute_db("UPDATE users SET status = ? WHERE user_id = ?", (status, doc['user_id']))

    @staticmethod
    def update_doctor_profile(doctor_id, name, specialization, qualification, experience, department, demo_phone, permission_level, status, email=None, profile_photo=None):
        if profile_photo:
            execute_db('''
                UPDATE doctors
                SET name = ?, specialization = ?, specialty = ?, qualification = ?, experience = ?,
                    department = ?, demo_phone = ?, permission_level = ?, status = ?, profile_photo = ?,
                    email = coalesce(?, email)
                WHERE doctor_id = ?
            ''', (name, specialization, specialization, qualification, experience, department, demo_phone, permission_level, status, profile_photo, email, doctor_id))
        else:
            execute_db('''
                UPDATE doctors
                SET name = ?, specialization = ?, specialty = ?, qualification = ?, experience = ?,
                    department = ?, demo_phone = ?, permission_level = ?, status = ?,
                    email = coalesce(?, email)
                WHERE doctor_id = ?
            ''', (name, specialization, specialization, qualification, experience, department, demo_phone, permission_level, status, email, doctor_id))

        doc = query_db("SELECT user_id FROM doctors WHERE doctor_id = ?", (doctor_id,), one=True)
        if doc:
            execute_db('''
                UPDATE users
                SET name = ?, email = coalesce(?, email), status = ?
                WHERE user_id = ?
            ''', (name, email, status, doc['user_id']))

    @staticmethod
    def update_own_doctor_profile(doctor_id, name, specialization, qualification, experience, department, demo_phone, email=None, profile_photo=None):
        if profile_photo:
            execute_db('''
                UPDATE doctors
                SET name = ?, specialization = ?, specialty = ?, qualification = ?, experience = ?,
                    department = ?, demo_phone = ?, profile_photo = ?,
                    email = coalesce(?, email)
                WHERE doctor_id = ?
            ''', (name, specialization, specialization, qualification, experience, department, demo_phone, profile_photo, email, doctor_id))
        else:
            execute_db('''
                UPDATE doctors
                SET name = ?, specialization = ?, specialty = ?, qualification = ?, experience = ?,
                    department = ?, demo_phone = ?,
                    email = coalesce(?, email)
                WHERE doctor_id = ?
            ''', (name, specialization, specialization, qualification, experience, department, demo_phone, email, doctor_id))

        doc = query_db("SELECT user_id FROM doctors WHERE doctor_id = ?", (doctor_id,), one=True)
        if doc:
            execute_db('''
                UPDATE users
                SET name = ?, email = coalesce(?, email)
                WHERE user_id = ?
            ''', (name, email, doc['user_id']))

    @staticmethod
    def remove_doctor_photo(doctor_id):
        execute_db("UPDATE doctors SET profile_photo = NULL WHERE doctor_id = ?", (doctor_id,))

    @staticmethod
    def set_doctor_status(doctor_id, status):
        execute_db("UPDATE doctors SET status = ? WHERE doctor_id = ?", (status, doctor_id))
        doc = query_db("SELECT user_id FROM doctors WHERE doctor_id = ?", (doctor_id,), one=True)
        if doc:
            execute_db("UPDATE users SET status = ? WHERE user_id = ?", (status, doc['user_id']))

    @staticmethod
    def get_device(device_id):
        return query_db("SELECT * FROM device_status WHERE device_id = ?", (device_id,), one=True)

    @staticmethod
    def generate_unique_doctor_id():
        rows = query_db("SELECT doctor_id FROM doctors")
        nums = []
        for r in rows:
            did = r['doctor_id']
            if did and did.startswith('DOC'):
                try:
                    nums.append(int(did.replace('DOC', '')))
                except ValueError:
                    pass
            elif did and did.startswith('D'):
                try:
                    nums.append(int(did.replace('D', '')))
                except ValueError:
                    pass
        next_num = (max(nums) + 1) if nums else 1
        candidate = f"DOC{next_num:03d}"
        while query_db("SELECT id FROM doctors WHERE doctor_id = ?", (candidate,), one=True):
            next_num += 1
            candidate = f"DOC{next_num:03d}"
        return candidate

    @staticmethod
    def get_patient_by_user_id(user_id):
        return query_db("SELECT * FROM patients WHERE user_id = ?", (user_id,), one=True)

    @staticmethod
    def get_all_devices():
        return query_db("SELECT * FROM device_status ORDER BY device_status ASC, device_id ASC")

    @staticmethod
    def create_doctor(doctor_id, name, specialization, qualification, experience,
                      department, demo_phone, email, permission_level='NORMAL',
                      status='active', profile_photo=None, username=None, password_hash=None, user_id=None):
        import uuid
        if not user_id:
            user_uid = f"USR-{uuid.uuid4().hex[:8].upper()}"
        else:
            user_uid = user_id
        if not username:
            username = f"doc_{doctor_id.lower()}"
        if not password_hash:
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash('DoctorDemo#2026!')

        execute_db('''
            INSERT INTO users (user_id, username, password_hash, role, name, email, status)
            VALUES (?, ?, ?, 'doctor', ?, ?, ?)
        ''', (user_uid, username, password_hash, name, email, status))

        execute_db('''
            INSERT INTO doctors (
                doctor_id, user_id, name, profile_photo, specialty, specialization,
                qualification, experience, department, email, demo_phone,
                permission_level, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            doctor_id, user_uid, name, profile_photo, specialization, specialization,
            qualification, experience, department, email, demo_phone,
            permission_level, status
        ))

        device_id = f"DEV-{doctor_id}-STATION"
        execute_db('''
            INSERT OR IGNORE INTO device_status (device_id, user_id, device_name, device_status, risk_contribution)
            VALUES (?, ?, ?, 'TRUSTED', -5)
        ''', (device_id, user_uid, f"Clinician Station - {name}"))

        return doctor_id

    @staticmethod
    def delete_doctor(doctor_id):
        doc = query_db("SELECT user_id, name FROM doctors WHERE doctor_id = ?", (doctor_id,), one=True)
        if doc:
            execute_db("DELETE FROM doctor_patient_assignments WHERE doctor_id = ?", (doctor_id,))
            execute_db("DELETE FROM doctors WHERE doctor_id = ?", (doctor_id,))
            execute_db("DELETE FROM users WHERE user_id = ?", (doc['user_id'],))
            return doc
        return None

