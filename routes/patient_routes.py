import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.patient import Patient
from services.auth_service import AuthService
from services.risk_engine import RiskEngine
from services.threat_detector import ThreatDetector
from services.deception_service import DeceptionService
from services.audit_service import AuditService

patient_bp = Blueprint('patient', __name__)

def current_user():
    if 'user_id' not in session:
        return None
    return AuthService.get_user_by_id(session['user_id'])

@patient_bp.route('/patient/<patient_id>')
def patient_detail(patient_id):
    user = current_user()
    
    # 1. EVALUATE RISK-BASED ACCESS CONTROL
    risk_eval = RiskEngine.evaluate_request(
        user=user,
        target_patient_id=patient_id,
        request_obj=request,
        resource_name='PATIENT_CHART'
    )

    # 2. CHECK IF THREAT DETECTED OR CRITICAL RISK (Score > 60)
    if risk_eval['score'] > 60:
        # Trigger Threat Detector
        threat = ThreatDetector.process_threat(
            user=user,
            request_obj=request,
            risk_result=risk_eval,
            target_patient_id=patient_id,
            action_name='VIEW_PATIENT_CHART'
        )

        # Log Honeypot Deception Telemetry
        DeceptionService.log_interaction(
            request_obj=request,
            user=user,
            decoy_patient_id=patient_id,
            action_performed='UNAUTHORIZED_CHART_ACCESS_INTERCEPTED',
            behavior_notes=f"User {user.get('user_id') if user else 'UNKNOWN'} attempted access to '{patient_id}'. Shielded by Decoy Environment."
        )

        # Tamper-evident Audit Log
        AuditService.log(
            action='UNAUTHORIZED_PATIENT_ACCESS',
            risk_result=risk_eval,
            user=user,
            request_obj=request,
            patient_id=patient_id,
            resource='PATIENT_CHART',
            details=f"CRITICAL: Unauthorized attempt on {patient_id}. Real data blocked; Decoy served."
        )

        # Fetch isolated DECOY record
        patient_data = DeceptionService.get_decoy_patient(patient_id)
        
        flash("⚠️ Security Alert: Access risk threshold exceeded. Session restricted to isolated decoy environment.", "danger")
        
        return render_template(
            'patient_detail.html',
            patient=patient_data,
            user=user,
            risk_eval=risk_eval,
            is_decoy=True,
            threat_event=threat
        )

    # 3. LOW / MEDIUM RISK: FETCH REAL SYNTHETIC PATIENT RECORD
    patient_data = Patient.get_by_id_real(patient_id)
    if not patient_data:
        # If not found in real DB, check decoy
        patient_data = DeceptionService.get_decoy_patient(patient_id)
        is_decoy = True
    else:
        is_decoy = False

    AuditService.log(
        action='VIEW_PATIENT_RECORD',
        risk_result=risk_eval,
        user=user,
        request_obj=request,
        patient_id=patient_id,
        resource='PATIENT_CHART',
        details=f"Authorized clinician {user['name']} accessed chart for {patient_data.get('name')}"
    )

    return render_template(
        'patient_detail.html',
        patient=patient_data,
        user=user,
        risk_eval=risk_eval,
        is_decoy=is_decoy,
        threat_event=None
    )

@patient_bp.route('/patient/<patient_id>/update-notes', methods=['POST'])
def update_clinical_notes(patient_id):
    user = current_user()
    if not user or user.get('role') not in ('doctor', 'admin'):
        flash("Unauthorized to modify clinical records.", "danger")
        return redirect(url_for('auth.login'))

    # Evaluate risk
    risk_eval = RiskEngine.evaluate_request(
        user=user,
        target_patient_id=patient_id,
        request_obj=request,
        resource_name='UPDATE_CLINICAL_NOTES'
    )

    if risk_eval['score'] > 60:
        ThreatDetector.process_threat(user, request, risk_eval, patient_id, 'UPDATE_CLINICAL_NOTES')
        flash("⚠️ Security policy violation: Update rejected due to elevated risk.", "danger")
        return redirect(url_for('patient.patient_detail', patient_id=patient_id))

    new_notes = request.form.get('clinical_notes', '').strip()
    Patient.update_notes(patient_id, new_notes)

    AuditService.log(
        action='UPDATE_CLINICAL_NOTES',
        risk_result=risk_eval,
        user=user,
        request_obj=request,
        patient_id=patient_id,
        resource='CLINICAL_RECORD',
        details=f"Clinical notes updated by Dr. {user['name']}"
    )

    flash("Patient clinical notes updated successfully.", "success")
    return redirect(url_for('patient.patient_detail', patient_id=patient_id))

@patient_bp.route('/patient/<patient_id>/add-prescription', methods=['POST'])
def add_prescription(patient_id):
    user = current_user()
    if not user or user.get('role') not in ('doctor', 'admin'):
        flash("Unauthorized to prescribe medication.", "danger")
        return redirect(url_for('auth.login'))

    risk_eval = RiskEngine.evaluate_request(
        user=user,
        target_patient_id=patient_id,
        request_obj=request,
        resource_name='ADD_PRESCRIPTION'
    )

    if risk_eval['score'] > 60:
        ThreatDetector.process_threat(user, request, risk_eval, patient_id, 'ADD_PRESCRIPTION')
        flash("⚠️ Prescription rejected by Risk Control Policy.", "danger")
        return redirect(url_for('patient.patient_detail', patient_id=patient_id))

    drug = request.form.get('drug', '').strip()
    dose = request.form.get('dose', '').strip()
    route = request.form.get('route', 'Oral').strip()
    frequency = request.form.get('frequency', 'Daily').strip()

    if drug and dose:
        Patient.add_prescription(patient_id, drug, dose, route, frequency)
        AuditService.log(
            action='ADD_PRESCRIPTION',
            risk_result=risk_eval,
            user=user,
            request_obj=request,
            patient_id=patient_id,
            resource='PHARMACY_ORDER',
            details=f"Prescription '{drug} {dose} ({route})' added by Dr. {user['name']}"
        )
        flash(f"Prescription for {drug} added successfully.", "success")
    else:
        flash("Drug name and dosage are required.", "warning")

    return redirect(url_for('patient.patient_detail', patient_id=patient_id))

@patient_bp.route('/api/patient/<patient_id>/vitals')
def api_patient_vitals(patient_id):
    """API endpoint providing real-time heart vitals and rhythm telemetry."""
    user = current_user()
    risk_eval = RiskEngine.evaluate_request(user=user, target_patient_id=patient_id, request_obj=request)

    if risk_eval['score'] > 60:
        decoy = DeceptionService.get_decoy_patient(patient_id)
        return jsonify({
            'status': 'DECOY',
            'vitals': decoy.get('vitals'),
            'risk': risk_eval
        })

    p = Patient.get_by_id_real(patient_id)
    if not p:
        return jsonify({'error': 'Patient not found'}), 404

    return jsonify({
        'status': 'REAL',
        'vitals': p.get('vitals'),
        'risk': risk_eval
    })
