from models.user import UserModel
from models.patient import PatientModel

class AuthorizationService:
    """Centralized server-side authorization and RBAC verification."""

    @classmethod
    def can_access_patient(cls, user, patient_id):
        """
        Verifies if clinician is assigned or holds active emergency access.
        Returns: (is_authorized: bool, reason: str, is_emergency: bool)
        """
        if not user:
            return False, "Unauthenticated session", False

        role = user.get('role')
        if role == 'admin':
            return True, "Security Administrator clearance", False

        if role == 'doctor':
            doc = UserModel.get_doctor_by_user_id(user.get('user_id'))
            if not doc:
                return False, "Doctor profile not configured", False

            doctor_id = doc['doctor_id']

            # Check 1: Primary care assignment
            if PatientModel.is_assigned(doctor_id, patient_id):
                return True, f"Patient {patient_id} assigned to Doctor {doctor_id}", False

            # Check 2: Active emergency break-glass grant
            if PatientModel.has_emergency_access(doctor_id, patient_id):
                return True, f"Emergency break-glass active for Doctor {doctor_id}", True

            return False, f"Patient {patient_id} is not assigned to Doctor {doctor_id}", False

        if role == 'patient':
            pat = PatientModel.get_by_user_id(user.get('user_id'))
            if pat and pat['patient_id'] == patient_id:
                return True, f"Patient {patient_id} viewing personal medical chart", False
            return False, f"Unauthorized cross-patient inquiry. Access restricted to personal records only.", False

        return False, "Role unauthorized for clinical records", False

    @classmethod
    def can_access_sensitivity(cls, user, record_sensitivity):
        """
        Verifies if user's permission level satisfies record sensitivity.
        """
        if not user:
            return False, "Unauthenticated session"

        if user.get('role') == 'admin':
            return True, "Administrator clearance"

        doc = UserModel.get_doctor_by_user_id(user.get('user_id'))
        if not doc:
            return False, "Clinician profile missing"

        doc_perm = doc.get('permission_level', 'NORMAL')
        allowed = PatientModel.can_access_sensitivity(doc_perm, record_sensitivity)

        if allowed:
            return True, f"Permission {doc_perm} satisfies {record_sensitivity}"
        return False, f"Insufficient permission: Requires {record_sensitivity}, doctor holds {doc_perm}"
