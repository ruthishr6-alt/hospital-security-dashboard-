from datetime import datetime
from collections import defaultdict
from database.db import query_db, execute_db

# Velocity tracking for bulk queries / rapid scraping: ip -> list of timestamps
_api_request_window = defaultdict(list)

class RiskEngine:
    """
    Dynamic Risk-Based Access Control Engine (0 - 100).
    Evaluates:
      - Authorized doctor: -10
      - Assigned patient: -10
      - Trusted device: -5
      - Unknown device/session: +20
      - Unusual access time: +15
      - Repeated failed login: +25
      - Unauthorized patient access: +20
      - Bulk record access: +30
      - Repeated suspicious API requests: +25
      - Attempt to access admin-only page: +30
      - Emergency break-glass access: +15
    Never allows risk score below 0 or above 100.
    """

    @classmethod
    def calculate_risk(cls, user=None, action='VIEW_PATIENT', patient=None, session_context=None):
        """
        Calculates dynamic risk score (0-100), level, and granular reasons.
        """
        session_context = session_context or {}
        score = 25 # Baseline initial score
        reasons = []

        ip_address = session_context.get('ip_address', '127.0.0.1')
        device_id = session_context.get('device_id', '')
        device_status = session_context.get('device_status', 'UNKNOWN')
        is_emergency = session_context.get('is_emergency', False)
        is_bulk = session_context.get('is_bulk', False)
        is_suspicious_api = session_context.get('is_suspicious_api', False)

        # 1. User Identity & Doctor Role Check
        if user and user.get('role') == 'doctor':
            score -= 10
            reasons.append({
                'factor': 'Authorized Doctor Role',
                'delta': -10,
                'type': 'CREDENTIAL',
                'description': f"Clinician authenticated: {user.get('name')}"
            })
        elif user and user.get('role') == 'admin':
            score -= 15
            reasons.append({
                'factor': 'Authorized Security Admin',
                'delta': -15,
                'type': 'CREDENTIAL',
                'description': f"Administrator authenticated: {user.get('name')}"
            })
        elif user and user.get('role') == 'patient':
            score -= 10
            reasons.append({
                'factor': 'Authenticated Patient Role',
                'delta': -10,
                'type': 'CREDENTIAL',
                'description': f"Patient authenticated: {user.get('name')}"
            })
        else:
            score += 25
            reasons.append({
                'factor': 'Unauthenticated / Anonymous Access',
                'delta': +25,
                'type': 'THREAT',
                'description': 'Anonymous or unauthenticated session attempting clinical resources'
            })

        # 2. Patient-Specific Assignment Check
        if patient and user and user.get('role') == 'doctor':
            from models.patient import PatientModel
            from models.user import UserModel
            doc = UserModel.get_doctor_by_user_id(user.get('user_id'))
            doctor_id = doc['doctor_id'] if doc else None

            patient_id = patient.get('patient_id') if isinstance(patient, dict) else str(patient)
            
            if doctor_id and PatientModel.is_assigned(doctor_id, patient_id):
                score -= 10
                reasons.append({
                    'factor': 'Assigned Patient Relationship',
                    'delta': -10,
                    'type': 'AUTHORIZATION',
                    'description': f"Patient {patient_id} is on Doctor {doctor_id}'s assigned clinical care roster"
                })
            elif is_emergency:
                # Emergency break-glass applied
                score += 15
                reasons.append({
                    'factor': 'Emergency Break-Glass Override',
                    'delta': +15,
                    'type': 'OVERRIDE',
                    'description': f"Temporary emergency access utilized for unassigned patient {patient_id}"
                })
            else:
                score += 20
                reasons.append({
                    'factor': 'Unauthorized Patient Access',
                    'delta': +20,
                    'type': 'VIOLATION',
                    'description': f"Doctor {doctor_id} attempting unassigned patient {patient_id} without emergency clearance"
                })
        elif patient and user and user.get('role') == 'patient':
            from models.patient import PatientModel
            pat = PatientModel.get_by_user_id(user.get('user_id'))
            patient_id = patient.get('patient_id') if isinstance(patient, dict) else str(patient)
            if pat and pat['patient_id'] == patient_id:
                score -= 10
                reasons.append({
                    'factor': 'Personal Health Record Access',
                    'delta': -10,
                    'type': 'AUTHORIZATION',
                    'description': f"Patient {patient_id} viewing verified personal health record"
                })
            else:
                score += 30
                reasons.append({
                    'factor': 'Cross-Patient Access Violation',
                    'delta': +30,
                    'type': 'VIOLATION',
                    'description': f"Patient attempting unauthorized access to another patient's medical record"
                })

        # 3. Trusted vs Unknown Device
        if device_status == 'TRUSTED':
            score -= 5
            reasons.append({
                'factor': 'Trusted Device Verification',
                'delta': -5,
                'type': 'DEVICE',
                'description': f"Hardware terminal ({device_id}) registered in hospital trust database"
            })
        else:
            score += 20
            reasons.append({
                'factor': 'Unknown Device / Unverified Session',
                'delta': +20,
                'type': 'DEVICE_RISK',
                'description': f"Access originated from unverified external hardware ({device_id or 'UNKNOWN'})"
            })

        # 4. Unusual Access Time (Outside 06:00 to 22:00 hospital standard hours)
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour >= 23:
            score += 15
            reasons.append({
                'factor': 'Unusual Access Time',
                'delta': +15,
                'type': 'TEMPORAL',
                'description': f"Access attempt occurred during off-peak night hours ({current_hour:02d}:00 hrs)"
            })

        # 5. Repeated Failed Logins Check for IP
        from services.auth_service import AuthService
        failed_count = AuthService.get_failed_attempts(ip_address)
        if failed_count >= 3:
            score += 25
            reasons.append({
                'factor': 'Repeated Failed Login Telemetry',
                'delta': +25,
                'type': 'BRUTE_FORCE',
                'description': f"Multiple consecutive failed authentication attempts ({failed_count}) recorded from IP {ip_address}"
            })

        # 6. Bulk Record Access
        if is_bulk or action in ('BULK_PATIENT_SEARCH', 'BULK_SCRAPE'):
            score += 30
            reasons.append({
                'factor': 'Bulk Record Harvesting Pattern',
                'delta': +30,
                'type': 'EXFILTRATION',
                'description': 'Rapid or unbounded query spanning multiple patient records simultaneously'
            })

        # 7. Repeated Suspicious API Requests / Injections
        if is_suspicious_api or session_context.get('sqli_detected', False):
            score += 25
            reasons.append({
                'factor': 'Repeated Suspicious API Requests',
                'delta': +25,
                'type': 'EXPLOIT',
                'description': 'Malicious query syntax, abnormal query bursts, or script injection tokens detected'
            })

        # 8. Attempt to Access Admin-Only Page
        if action in ('ADMIN_PAGE_ACCESS', 'ADMIN_SETTINGS_PROBE') and (not user or user.get('role') != 'admin'):
            score += 30
            reasons.append({
                'factor': 'Attempt to Access Admin-Only Page',
                'delta': +30,
                'type': 'PRIVILEGE_ESCALATION',
                'description': 'Non-administrative identity attempting to access security configuration endpoints'
            })

        # 9. Record Sensitivity Level Check (CONFIDENTIAL / HIGHLY_CONFIDENTIAL)
        if patient and isinstance(patient, dict) and user and user.get('role') == 'doctor':
            from models.patient import PatientModel
            from models.user import UserModel
            doc = UserModel.get_doctor_by_user_id(user.get('user_id'))
            doc_perm = doc['permission_level'] if doc else 'NORMAL'
            rec_sens = patient.get('record_sensitivity_level', 'NORMAL')
            
            if not PatientModel.can_access_sensitivity(doc_perm, rec_sens) and not is_emergency:
                score += 25
                reasons.append({
                    'factor': 'Record Sensitivity Clearance Exceeded',
                    'delta': +25,
                    'type': 'CONFIDENTIAL_VIOLATION',
                    'description': f"Record requires {rec_sens} clearance; clinician holds {doc_perm}"
                })

        # Strictly clamp risk score between 0 and 100
        final_score = max(0, min(100, score))

        # Categorize Risk Level
        if final_score <= 30:
            level = 'LOW'
        elif final_score <= 60:
            level = 'MEDIUM'
        elif final_score <= 80:
            level = 'HIGH'
        else:
            level = 'CRITICAL'

        # Record event in risk_scores table if session_id is provided
        session_id = session_context.get('session_id')
        user_id = user.get('user_id') if user else 'UNKNOWN'
        if session_id:
            try:
                execute_db('''
                    INSERT INTO risk_scores (user_id, session_id, current_score, risk_level, last_evaluated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, session_id) DO UPDATE SET
                        current_score = excluded.current_score,
                        risk_level = excluded.risk_level,
                        last_evaluated_at = CURRENT_TIMESTAMP
                ''', (user_id, session_id, final_score, level))
            except Exception:
                pass

        return {
            'score': final_score,
            'level': level,
            'reasons': reasons,
            'is_critical': final_score > 60
        }
