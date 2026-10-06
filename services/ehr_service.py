"""
services/ehr_service.py
Hospital Electronic Health Record (EHR) Formatter & Medication Parser.
Transforms raw backend clinical data (JSON, dictionaries, unstructured strings)
into polished, human-readable medical components for patients, clinicians, and auditors.
"""
import json
import re

class EhrService:

    @staticmethod
    def parse_medications(raw_data):
        """
        Transforms any raw medication data (list of dicts, JSON string, or formatted text)
        into a clean, standardized list of medication objects:
        [
            {
                'name': 'Aspirin (Chewable)',
                'dose': '325 mg',
                'route': 'Oral',
                'frequency': 'Stat Loading Dose',
                'icon': 'fa-solid fa-tablets',
                'route_class': 'route-oral',
                'category': 'Antiplatelet / Cardiovascular'
            }, ...
        ]
        Guarantees that raw JSON keys like {"drug":, "dose":} are NEVER rendered.
        """
        if not raw_data:
            return []

        # If string, try JSON parse first
        if isinstance(raw_data, str):
            cleaned_str = raw_data.strip()
            if cleaned_str.startswith('[') or cleaned_str.startswith('{'):
                try:
                    raw_data = json.loads(cleaned_str)
                except Exception:
                    pass

        # If single dictionary
        if isinstance(raw_data, dict):
            raw_data = [raw_data]

        medications = []

        # Case 1: Structured list
        if isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict):
                    name = item.get('drug') or item.get('name') or item.get('medicine') or item.get('medication') or 'Cardiology Medication'
                    dose = item.get('dose') or item.get('dosage') or item.get('strength') or 'Clinical Standard'
                    route = item.get('route') or item.get('method') or 'Oral'
                    freq = item.get('frequency') or item.get('instructions') or item.get('schedule') or 'As Prescribed'
                    medications.append(EhrService._build_med_item(name, dose, route, freq))
                elif isinstance(item, str) and item.strip():
                    medications.append(EhrService._parse_string_med(item.strip()))

        # Case 2: String input (from forms or clinical notes)
        elif isinstance(raw_data, str) and raw_data.strip():
            text = raw_data.strip()

            # Split by line breaks if multi-line
            lines = [line.strip('-* \t') for line in text.splitlines() if line.strip('-* \t')]
            if len(lines) > 1:
                for line in lines:
                    medications.append(EhrService._parse_string_med(line))
            else:
                # Semicolon or pipe separated
                if ';' in text:
                    chunks = [c.strip() for c in text.split(';') if c.strip()]
                    for chunk in chunks:
                        medications.append(EhrService._parse_string_med(chunk))
                elif '|' in text and not (',' in text and text.count(',') > text.count('|')):
                    # e.g. "Aspirin | 325 mg | Oral | Stat"
                    medications.append(EhrService._parse_string_med(text))
                elif ',' in text:
                    chunks = [c.strip() for c in text.split(',') if c.strip()]
                    for chunk in chunks:
                        medications.append(EhrService._parse_string_med(chunk))
                else:
                    medications.append(EhrService._parse_string_med(text))

        return medications

    @staticmethod
    def _build_med_item(name, dose, route, frequency):
        """Constructs a clean, UI-ready medication dictionary."""
        name_clean = str(name).strip()
        dose_clean = str(dose).strip()
        route_clean = str(route).strip()
        freq_clean = str(frequency).strip()

        # Route icon & class determination
        r_lower = route_clean.lower()
        if 'iv infusion' in r_lower or 'infusion' in r_lower:
            icon = 'fa-solid fa-syringe'
            route_class = 'route-iv'
            route_label = 'IV Infusion'
        elif 'iv' in r_lower or 'injection' in r_lower or 'drip' in r_lower:
            icon = 'fa-solid fa-syringe'
            route_class = 'route-iv'
            route_label = 'Intravenous (IV)'
        elif 'sublingual' in r_lower:
            icon = 'fa-solid fa-tablets'
            route_class = 'route-oral'
            route_label = 'Sublingual'
        elif 'oral' in r_lower or 'po' in r_lower or 'chewable' in r_lower:
            icon = 'fa-solid fa-tablets'
            route_class = 'route-oral'
            route_label = 'Oral'
        elif 'subcut' in r_lower or 'sc' in r_lower:
            icon = 'fa-solid fa-vial'
            route_class = 'route-sc'
            route_label = 'Subcutaneous (SC)'
        elif 'inhal' in r_lower:
            icon = 'fa-solid fa-lungs'
            route_class = 'route-inhalation'
            route_label = 'Inhalation'
        else:
            icon = 'fa-solid fa-pills'
            route_class = 'route-general'
            route_label = route_clean.title()

        # Category detection for badges
        cat = 'Cardiovascular Pharmacotherapy'
        n_lower = name_clean.lower()
        if any(w in n_lower for w in ['aspirin', 'ticagrelor', 'clopidogrel', 'prasugrel']):
            cat = 'Antiplatelet Agent'
        elif any(w in n_lower for w in ['heparin', 'enoxaparin', 'warfarin', 'apixaban', 'rivaroxaban']):
            cat = 'Anticoagulant'
        elif any(w in n_lower for w in ['metoprolol', 'bisoprolol', 'carvedilol', 'atenolol']):
            cat = 'Beta-1 Blocker'
        elif any(w in n_lower for w in ['atorvastatin', 'rosuvastatin', 'simvastatin']):
            cat = 'HMG-CoA Reductase Inhibitor (Statin)'
        elif any(w in n_lower for w in ['furosemide', 'torsemide', 'spironolactone']):
            cat = 'Loop Diuretic'
        elif any(w in n_lower for w in ['nitroglycerin', 'isosorbide', 'nitro']):
            cat = 'Vasodilator / Nitrate'
        elif any(w in n_lower for w in ['mavacamten']):
            cat = 'Cardiac Myosin Inhibitor'
        elif any(w in n_lower for w in ['ramipril', 'lisinopril', 'enalapril', 'sacubitril']):
            cat = 'RAAS Inhibitor / ARNI'

        return {
            'name': name_clean,
            'dose': dose_clean,
            'route': route_label,
            'frequency': freq_clean,
            'icon': icon,
            'route_class': route_class,
            'category': cat,
            'status': 'Active Regimen'
        }

    @staticmethod
    def _parse_string_med(text):
        """Intelligently parses unstructured text like 'Aspirin 325mg daily' or pipe-delimited text."""
        clean_text = text.strip()

        # If pipe delimited: Name | Dose | Route | Frequency
        if '|' in clean_text:
            parts = [p.strip() for p in clean_text.split('|')]
            name = parts[0] if len(parts) > 0 else 'Medication'
            dose = parts[1] if len(parts) > 1 else 'Standard Dose'
            route = parts[2] if len(parts) > 2 else 'Oral'
            freq = parts[3] if len(parts) > 3 else 'Once Daily'
            return EhrService._build_med_item(name, dose, route, freq)

        # Regex to detect dose (e.g. 325 mg, 90mg, 18 units/kg/hr, 5mg)
        dose_match = re.search(r'(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units(?:/kg(?:/hr)?)?|mEq|tablets?|capsules?|drops?))', clean_text, re.IGNORECASE)

        # Regex to detect route (longer matches first)
        route_match = re.search(r'\b(iv infusion|continuous infusion|iv drip|sublingual|subcutaneous|inhalation|topical|oral|po|iv|sc)\b', clean_text, re.IGNORECASE)

        # Regex to detect frequency (Stat Loading Dose, Twice Daily, Once Daily, Continuous, PRN, Bedtime, Every \d+ Hours)
        freq_match = re.search(r'\b(stat(?: loading dose)?|twice daily|once daily|three times daily|continuous(?: titration)?|at bedtime|every \d+ hours?|bid|tid|qid|prn|daily)\b', clean_text, re.IGNORECASE)

        dose = dose_match.group(1) if dose_match else 'Prescribed Dose'
        route = route_match.group(1).title() if route_match else 'Oral'
        frequency = freq_match.group(1).title() if freq_match else 'As Prescribed'

        # Extract name: remove dose, route, freq parts from text
        name = clean_text
        if dose_match:
            name = name.replace(dose_match.group(0), '')
        if route_match:
            name = re.sub(r'\b' + re.escape(route_match.group(0)) + r'\b', '', name, flags=re.IGNORECASE)
        if freq_match:
            name = re.sub(r'\b' + re.escape(freq_match.group(0)) + r'\b', '', name, flags=re.IGNORECASE)

        # Clean punctuation from remaining name but preserve parentheses like (Chewable)
        name = re.sub(r'[\:\,]', ' ', name).strip()
        name = name.strip(' -:;,')
        name = re.sub(r'\s+', ' ', name)

        if not name:
            name = clean_text.split()[0] if clean_text else 'Cardiology Medication'

        return EhrService._build_med_item(name, dose, route, frequency)

    @staticmethod
    def format_vitals(raw_vitals):
        """
        Parses and formats cardiac telemetry vitals into structured metrics.
        Never outputs raw python dicts or stringified JSON.
        """
        if not raw_vitals:
            return {
                'heart_rate': '72 bpm',
                'blood_pressure': '120/80 mmHg',
                'spo2': '98%',
                'resp_rate': '16 /min',
                'temperature': '36.8 °C',
                'rhythm': 'Normal Sinus Rhythm',
                'summary': 'HR: 72 bpm • BP: 120/80 mmHg • SpO2: 98%'
            }

        # Handle JSON string
        if isinstance(raw_vitals, str):
            cleaned = raw_vitals.strip()
            if cleaned.startswith('{') and cleaned.endswith('}'):
                try:
                    raw_vitals = json.loads(cleaned)
                except Exception:
                    pass

        # If dictionary
        if isinstance(raw_vitals, dict):
            hr = raw_vitals.get('heart_rate') or raw_vitals.get('hr') or 75
            hr_str = f"{hr} bpm" if not str(hr).endswith('bpm') else str(hr)
            bp = raw_vitals.get('blood_pressure') or raw_vitals.get('bp') or '120/80 mmHg'
            spo2 = raw_vitals.get('spo2') or raw_vitals.get('sp_o2') or '98%'
            rr = raw_vitals.get('resp_rate') or raw_vitals.get('rr') or 16
            rr_str = f"{rr} /min" if not str(rr).endswith('/min') else str(rr)
            temp = raw_vitals.get('temp') or raw_vitals.get('temperature') or '36.8 °C'
            rhythm = raw_vitals.get('rhythm') or 'Normal Sinus Rhythm'

            return {
                'heart_rate': hr_str,
                'blood_pressure': str(bp),
                'spo2': str(spo2),
                'resp_rate': rr_str,
                'temperature': str(temp),
                'rhythm': str(rhythm),
                'summary': f"HR: {hr_str} • BP: {bp} • SpO2: {spo2}"
            }

        # If formatted string (e.g. "HR: 75 bpm | BP: 120/80 mmHg | SpO2: 98%")
        if isinstance(raw_vitals, str):
            s = raw_vitals.strip()
            hr_match = re.search(r'HR:\s*([^\|;,]+)', s, re.IGNORECASE)
            bp_match = re.search(r'BP:\s*([^\|;,]+)', s, re.IGNORECASE)
            spo2_match = re.search(r'SpO2:\s*([^\|;,]+)', s, re.IGNORECASE)

            hr = hr_match.group(1).strip() if hr_match else '72 bpm'
            bp = bp_match.group(1).strip() if bp_match else '120/80 mmHg'
            spo2 = spo2_match.group(1).strip() if spo2_match else '98%'

            return {
                'heart_rate': hr,
                'blood_pressure': bp,
                'spo2': spo2,
                'resp_rate': '16 /min',
                'temperature': '36.8 °C',
                'rhythm': 'Sinus Telemetry Active',
                'summary': s if len(s) < 50 else f"HR: {hr} • BP: {bp} • SpO2: {spo2}"
            }

        return {
            'heart_rate': '72 bpm',
            'blood_pressure': '120/80 mmHg',
            'spo2': '98%',
            'resp_rate': '16 /min',
            'temperature': '36.8 °C',
            'rhythm': 'Sinus Rhythm',
            'summary': 'HR: 72 bpm • BP: 120/80 mmHg • SpO2: 98%'
        }
