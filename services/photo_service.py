import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIRS = {
    'doctor': os.path.join(BASE_DIR, 'static', 'uploads', 'doctors'),
    'patient': os.path.join(BASE_DIR, 'static', 'uploads', 'patients'),
    'decoy': os.path.join(BASE_DIR, 'static', 'uploads', 'decoys')
}

# Ensure folders exist
for folder in UPLOAD_DIRS.values():
    os.makedirs(folder, exist_ok=True)

class PhotoService:
    @staticmethod
    def is_allowed_file(filename):
        if not filename or '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in ALLOWED_EXTENSIONS

    @staticmethod
    def validate_and_save(file_storage, category='doctor'):
        """
        Validates uploaded file:
        - Checks extension
        - Validates magic bytes
        - Ensures safe random unique filename
        - Returns (filename, None) on success or (None, error_message)
        """
        if not file_storage or not file_storage.filename:
            return None, "No file provided"

        filename = secure_filename(file_storage.filename)
        if not PhotoService.is_allowed_file(filename):
            return None, "Invalid file format. Allowed formats: JPG, JPEG, PNG, WEBP"

        # Read first bytes to verify image header magic bytes
        header = file_storage.read(16)
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)

        if size > MAX_FILE_SIZE:
            return None, "File size exceeds the 5MB maximum limit"

        # Check basic image magic bytes
        # JPEG: \xff\xd8\xff
        # PNG: \x89PNG\r\n\x1a\n
        # WEBP: RIFF....WEBP
        is_jpeg = header.startswith(b'\xff\xd8\xff')
        is_png = header.startswith(b'\x89PNG\r\n\x1a\n')
        is_webp = header.startswith(b'RIFF') and b'WEBP' in header[:16]

        if not (is_jpeg or is_png or is_webp):
            return None, "Corrupted or non-image binary file detected"

        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'jpeg':
            ext = 'jpg'

        prefix = 'doc' if category == 'doctor' else ('pat' if category == 'patient' else 'dec')
        unique_name = f"{prefix}_{uuid.uuid4().hex[:12]}.{ext}"
        target_dir = UPLOAD_DIRS.get(category, UPLOAD_DIRS['doctor'])
        target_path = os.path.join(target_dir, unique_name)

        # Save securely
        file_storage.save(target_path)
        return unique_name, None

    @staticmethod
    def delete_photo(filename, category='doctor'):
        """Safely removes an uploaded photo without path traversal."""
        if not filename:
            return
        safe_name = os.path.basename(filename)
        target_dir = UPLOAD_DIRS.get(category, UPLOAD_DIRS['doctor'])
        target_path = os.path.join(target_dir, safe_name)
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass

    @staticmethod
    def get_doctor_photo_url(filename):
        if filename:
            safe_name = os.path.basename(filename)
            target_path = os.path.join(UPLOAD_DIRS['doctor'], safe_name)
            if os.path.exists(target_path):
                return f"/static/uploads/doctors/{safe_name}"
        return "/static/img/avatars/doctor_default.svg"

    @staticmethod
    def get_patient_photo_url(filename, is_decoy=False):
        if filename:
            safe_name = os.path.basename(filename)
            cat = 'decoy' if is_decoy else 'patient'
            target_path = os.path.join(UPLOAD_DIRS[cat], safe_name)
            if os.path.exists(target_path):
                return f"/static/uploads/{cat}s/{safe_name}"
            # Also check normal patient uploads
            normal_path = os.path.join(UPLOAD_DIRS['patient'], safe_name)
            if os.path.exists(normal_path):
                return f"/static/uploads/patients/{safe_name}"

        return "/static/img/avatars/decoy_default.svg" if is_decoy else "/static/img/avatars/patient_default.svg"
