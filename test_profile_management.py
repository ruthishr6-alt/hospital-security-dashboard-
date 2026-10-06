import sys
import os
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from database.seed import seed
from services.phone_service import PhoneService

class ProfileManagementTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed()
        cls.client = app.test_client()

    def test_01_phone_validation_and_masking(self):
        # Valid USA
        valid, formatted, err = PhoneService.validate_phone('+1 (555) 123-4567')
        self.assertTrue(valid)
        self.assertEqual(formatted, '+1 (555) 123-4567')

        # Valid India
        valid, formatted, err = PhoneService.validate_phone('+91 9876543210')
        self.assertTrue(valid)
        self.assertEqual(formatted, '+91 9876543210')

        # Invalid phone
        valid, formatted, err = PhoneService.validate_phone('123')
        self.assertFalse(valid)

        # Phone masking
        masked = PhoneService.mask_phone('+1 (555) 019-2830')
        self.assertIn('***', masked)
        self.assertTrue(masked.startswith('+1'))
        self.assertTrue(masked.endswith('30'))

        # Split country code
        cc, local = PhoneService.split_country_code('+44 7911 123456')
        self.assertEqual(cc, '+44')
        self.assertEqual(local, '7911 123456')

    def test_02_doctor_self_profile_update(self):
        # Login as doctor D001
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'U_DOC01'
            sess['username'] = 'dr_sarah'
            sess['role'] = 'doctor'
            sess['doctor_id'] = 'D001'
            sess['name'] = 'Dr. Sarah Lin, MD'
            sess['device_id'] = 'DEV-DOC01-TRUSTED'
            sess['device_status'] = 'TRUSTED'

        resp = self.client.post('/profile/edit', data={
            'name': 'Dr. Sarah Lin MD',
            'specialization': 'Senior Interventional Cardiologist',
            'qualification': 'MBBS, MD Cardiology, FACC',
            'experience': '14 Years',
            'department': 'Cardiac Critical Care Unit',
            'email': 'sarah.lin.update@heartsecure.internal',
            'country_code': '+1',
            'demo_phone': '(555) 999-4321'
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Senior Interventional Cardiologist', resp.data)
        self.assertIn(b'MBBS, MD Cardiology, FACC', resp.data)
        self.assertIn(b'+1 (555) 999-4321', resp.data)

    def test_03_admin_patient_creation_with_phone(self):
        # Login as admin
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'U_ADMIN01'
            sess['username'] = 'sec_admin'
            sess['role'] = 'admin'
            sess['name'] = 'System Security Administrator'
            sess['device_id'] = 'DEV-ADMIN-TRUSTED'
            sess['device_status'] = 'TRUSTED'

        resp = self.client.post('/admin/patients', data={
            'action_type': 'create_patient',
            'patient_id': 'HP999',
            'name': 'Demo Test Patient',
            'age': '65',
            'gender': 'Male',
            'blood_group': 'B+',
            'assigned_doctor_id': 'D001',
            'heart_condition_category': 'Test Cardiac Condition',
            'medical_history': 'Prior bypass surgery',
            'ecg_report': 'Normal sinus rhythm',
            'echo_report': 'EF 45%',
            'current_prescriptions': 'Aspirin 75mg',
            'emergency_contact': 'Test Contact +1 555-0000',
            'record_sensitivity_level': 'CONFIDENTIAL',
            'country_code': '+91',
            'phone_number': '9876543210'
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'HP999', resp.data)
        self.assertIn(b'+91 9876543210', resp.data)

    def test_04_patient_detail_phone_visibility(self):
        # 1. Assigned Doctor D001 views HP001 (assigned) -> Sees full phone
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'U_DOC01'
            sess['username'] = 'dr_sarah'
            sess['role'] = 'doctor'
            sess['doctor_id'] = 'D001'
            sess['name'] = 'Dr. Sarah Lin MD'
            sess['device_id'] = 'DEV-DOC01-TRUSTED'
            sess['device_status'] = 'TRUSTED'

        resp = self.client.get('/patient/HP001')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'VERIFIED', resp.data)

        # 2. Unassigned Doctor D002 probes HP001 (not assigned) -> Intercepted, shunted to Decoy Honeypot
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'U_DOC02'
            sess['username'] = 'dr_chen'
            sess['role'] = 'doctor'
            sess['doctor_id'] = 'D002'
            sess['name'] = 'Dr. Marcus Vance, MD'
            sess['device_id'] = 'DEV-DOC02-TRUSTED'
            sess['device_status'] = 'TRUSTED'

        resp = self.client.get('/patient/HP001')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'DECOY', resp.data)

if __name__ == '__main__':
    unittest.main()
