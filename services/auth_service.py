import random
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import query_db, execute_db

class AuthService:
    """Manages secure authentication, demo OTP issuance, and session telemetry."""

    @staticmethod
    def verify_credentials(username, password, ip_address='127.0.0.1'):
        """Verifies username and password hash. Tracks failed attempts."""
        user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        if not user or not check_password_hash(user['password_hash'], password):
            AuthService.record_failed_attempt(ip_address, username)
            return None, "Invalid username or password credentials"

        if user['status'] != 'active':
            return None, "Account is disabled. Please contact Security Administration."

        # Credentials valid: Generate a 6-digit Demo OTP
        demo_otp = str(random.randint(100000, 999999))
        return {
            'user': user,
            'demo_otp': demo_otp
        }, None

    @staticmethod
    def verify_otp(entered_otp, expected_otp):
        """Verifies the entered demo OTP."""
        if not entered_otp or not expected_otp:
            return False
        # Also allow demo master code '123456' for ease of testing
        return entered_otp.strip() == expected_otp.strip() or entered_otp.strip() == '123456'

    @staticmethod
    def record_failed_attempt(ip_address, username):
        execute_db('''
            INSERT INTO failed_logins (ip_address, username_attempted, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (ip_address, username or 'unknown'))

    @staticmethod
    def get_failed_attempts(ip_address, minutes_window=15):
        row = query_db('''
            SELECT COUNT(*) as cnt FROM failed_logins
            WHERE ip_address = ? AND timestamp >= datetime('now', ?)
        ''', (ip_address, f'-{minutes_window} minutes'), one=True)
        return row['cnt'] if row else 0

    @staticmethod
    def clear_failed_attempts(ip_address):
        execute_db("DELETE FROM failed_logins WHERE ip_address = ?", (ip_address,))
