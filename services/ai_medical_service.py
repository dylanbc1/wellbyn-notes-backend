"""
AI Medical Service - Generates medical notes, suggests codes, and creates CMS-1500 forms
Uses Google Gemini API
"""

import json
import logging
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from config import settings

logger = logging.getLogger(__name__)


class AIMedicalService:
    """
    Service for AI-powered medical workflow using Google Gemini:
    1. Generate medical note from transcription
    2. Suggest ICD-10 codes
    3. Suggest CPT codes + modifiers
    4. Generate CMS-1500 form data
    """
    
    def __init__(self):
        self.gemini_key = settings.GEMINI_KEY
        self.gemini_model_name = settings.GEMINI_MODEL
        
        # Configure Gemini
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                
                # First, try to list available models to find the correct one
                try:
                    available_models = []
                    for model in genai.list_models():
                        if 'generateContent' in model.supported_generation_methods:
                            model_name = model.name.replace('models/', '')
                            available_models.append(model_name)
                    
                    logger.info(f"Available Gemini models: {available_models}")
                    
                    # Try to find a flash model (free tier)
                    flash_models = [m for m in available_models if 'flash' in m.lower()]
                    if flash_models:
                        # Prefer gemini-2.5-flash, then gemini-1.5-flash, then any flash model
                        preferred_model = None
                        for preferred in ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-2.0-flash']:
                            if preferred in flash_models:
                                preferred_model = preferred
                                break
                        
                        if preferred_model:
                            self.gemini_model_name = preferred_model
                            logger.info(f"Using free Flash model: {preferred_model}")
                        else:
                            self.gemini_model_name = flash_models[0]
                            logger.info(f"Using available Flash model: {self.gemini_model_name}")
                    
                except Exception as e:
                    logger.warning(f"Could not list models: {e}, using configured model: {self.gemini_model_name}")
                
                # Initialize the model
                self.model = genai.GenerativeModel(self.gemini_model_name)
                logger.info(f"Initialized Gemini model: {self.gemini_model_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model '{self.gemini_model_name}': {e}")
                self.model = None
        else:
            logger.warning("GEMINI_KEY not configured. Using mock responses.")
            self.model = None
    
    def _call_gemini(self, prompt: str, system_instruction: str = "", temperature: float = 0.3) -> Optional[str]:
        """
        Call Google Gemini API with prompt
        
        Args:
            prompt: User prompt
            system_instruction: System instruction/context
            temperature: Sampling temperature (0.0-1.0)
            
        Returns:
            Generated text or None if error
        """
        if not self.model:
            logger.warning("Gemini model not available. Using mock responses.")
            return None
        
        try:
            # Combine system instruction and prompt
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            
            # Configure generation parameters
            generation_config = {
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return None
    
    def map_to_soap_continuous(self, transcription_text: str, existing_soap: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Mapea continuamente la transcripción a secciones SOAP
        Se ejecuta en tiempo real durante la visita
        
        Args:
            transcription_text: Texto de transcripción (puede ser incremental)
            existing_soap: Secciones SOAP existentes para actualizar
            
        Returns:
            Dict con secciones SOAP: {subjective: {text, locked}, objective: {...}, assessment: {...}, plan: {...}}
        """
        system_instruction = """You are a medical AI assistant that continuously maps clinical conversations into SOAP format (Subjective, Objective, Assessment, Plan). 
        Update sections incrementally as new information arrives. Do not suggest diagnoses, only organize information."""
        
        existing_text = ""
        if existing_soap:
            existing_text = f"""
Existing SOAP sections:
- Subjective: {existing_soap.get('subjective', {}).get('text', '')[:200]}
- Objective: {existing_soap.get('objective', {}).get('text', '')[:200]}
- Assessment: {existing_soap.get('assessment', {}).get('text', '')[:200]}
- Plan: {existing_soap.get('plan', {}).get('text', '')[:200]}
"""
        
        prompt = f"""Map the following clinical conversation excerpt into SOAP format. Update existing sections if provided.

{existing_text}

New transcription excerpt:
{transcription_text}

Return ONLY a valid JSON object with this exact structure:
{{
  "subjective": {{
    "text": "Patient-reported symptoms, history, chief complaint",
    "locked": false
  }},
  "objective": {{
    "text": "Observable findings, vital signs, physical exam",
    "locked": false
  }},
  "assessment": {{
    "text": "Clinical assessment and reasoning",
    "locked": false
  }},
  "plan": {{
    "text": "Treatment plan, medications, follow-up",
    "locked": false
  }}
}}

Return ONLY valid JSON, no additional text or markdown."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.2)
        
        if result:
            try:
                result = result.strip()
                # Remove markdown code blocks if present
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                # Try to find JSON object
                start_idx = result.find("{")
                end_idx = result.rfind("}") + 1
                if start_idx != -1 and end_idx > start_idx:
                    result = result[start_idx:end_idx]
                
                soap_data = json.loads(result)
                
                # Merge with existing if provided, preserving locked status
                if existing_soap:
                    for section in ['subjective', 'objective', 'assessment', 'plan']:
                        if existing_soap.get(section, {}).get('locked', False):
                            # Keep locked section unchanged
                            soap_data[section] = existing_soap[section]
                        else:
                            # Merge text if not locked
                            existing_text = existing_soap.get(section, {}).get('text', '')
                            new_text = soap_data.get(section, {}).get('text', '')
                            if existing_text and new_text:
                                soap_data[section]['text'] = f"{existing_text}\n{new_text}".strip()
                            soap_data[section]['locked'] = existing_soap.get(section, {}).get('locked', False)
                
                return soap_data
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing SOAP JSON: {e}")
                logger.debug(f"Response was: {result}")
        
        # Fallback: Return basic structure
        return {
            "subjective": {"text": transcription_text[:500] if transcription_text else "", "locked": False},
            "objective": {"text": "", "locked": False},
            "assessment": {"text": "", "locked": False},
            "plan": {"text": "", "locked": False}
        }
    
    def check_documentation_completeness(self, transcription_text: str, soap_sections: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Verifica la completitud de la documentación clínica
        
        Args:
            transcription_text: Texto de transcripción
            soap_sections: Secciones SOAP actuales
            
        Returns:
            Dict con estado de cada elemento: {chief_complaint: "complete|partial|missing", ...}
        """
        system_instruction = """You are a medical documentation quality checker. Analyze clinical documentation and identify missing or incomplete elements. Return only valid JSON."""
        
        soap_text = ""
        if soap_sections:
            soap_text = f"""
SOAP Sections:
- Subjective: {soap_sections.get('subjective', {}).get('text', '')}
- Objective: {soap_sections.get('objective', {}).get('text', '')}
- Assessment: {soap_sections.get('assessment', {}).get('text', '')}
- Plan: {soap_sections.get('plan', {}).get('text', '')}
"""
        
        prompt = f"""Analyze the following clinical documentation and assess completeness for each required element.

Transcription: {transcription_text[:1000]}

{soap_text}

For each element, determine if it is:
- "complete": Fully documented with sufficient detail
- "partial": Some information present but incomplete
- "missing": Not documented

Return ONLY valid JSON:
{{
  "chief_complaint": "complete|partial|missing",
  "duration": "complete|partial|missing",
  "severity": "complete|partial|missing",
  "location": "complete|partial|missing",
  "assessment": "complete|partial|missing",
  "plan": "complete|partial|missing"
}}

Return ONLY valid JSON, no additional text."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.2)
        
        if result:
            try:
                result = result.strip()
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                start_idx = result.find("{")
                end_idx = result.rfind("}") + 1
                if start_idx != -1 and end_idx > start_idx:
                    result = result[start_idx:end_idx]
                
                completeness = json.loads(result)
                return completeness
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing completeness JSON: {e}")
        
        # Fallback
        return {
            "chief_complaint": "partial",
            "duration": "missing",
            "severity": "missing",
            "location": "missing",
            "assessment": "partial",
            "plan": "partial"
        }
    
    def generate_clarification_nudges(self, transcription_text: str, soap_sections: Optional[Dict[str, Any]] = None, documentation_completeness: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Genera prompts no intrusivos para clarificación y desambiguación diagnóstica
        
        Args:
            transcription_text: Texto de transcripción
            soap_sections: Secciones SOAP actuales
            documentation_completeness: Estado de completitud
            
        Returns:
            Lista de nudges: [{type: "documentation|diagnostic", message: "...", category: "..."}, ...]
        """
        system_instruction = """You are a medical documentation assistant. Generate non-intrusive prompts to help complete documentation or clarify diagnostic information. 
        These are documentation completeness & safety checks, NOT decision support. Do NOT suggest diagnoses."""
        
        completeness_text = ""
        if documentation_completeness:
            missing = [k for k, v in documentation_completeness.items() if v == "missing"]
            partial = [k for k, v in documentation_completeness.items() if v == "partial"]
            if missing or partial:
                completeness_text = f"Missing elements: {', '.join(missing)}\nPartial elements: {', '.join(partial)}"
        
        prompt = f"""Based on the clinical documentation, suggest non-intrusive clarification prompts.

Transcription: {transcription_text[:1000]}

{completeness_text}

Generate prompts for:
1. Documentation clarifications (missing/partial elements)
2. Diagnostic disambiguation check questions (yes/no questions to rule out conditions, NOT diagnosis suggestions)

Return ONLY valid JSON array:
[
  {{
    "type": "documentation|diagnostic",
    "message": "Clear, concise prompt",
    "category": "pain_scale|laterality|duration|onset|neuro_check|cardiac_check|infectious_check|trauma_check",
    "priority": "high|medium|low"
  }}
]

Return ONLY valid JSON array, no additional text."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.3)
        
        if result:
            try:
                result = result.strip()
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                start_idx = result.find("[")
                end_idx = result.rfind("]") + 1
                if start_idx != -1 and end_idx > start_idx:
                    result = result[start_idx:end_idx]
                
                nudges = json.loads(result)
                if isinstance(nudges, list):
                    return nudges[:5]  # Limit to 5 nudges
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing nudges JSON: {e}")
        
        return []
    
    def generate_medical_note(self, transcription_text: str) -> str:
        """
        Generate a structured medical note from transcription
        
        Args:
            transcription_text: The transcribed audio text
            
        Returns:
            Formatted medical note
        """
        system_instruction = """You are a medical transcriptionist expert. Generate professional medical notes from audio transcriptions following SOAP format (Subjective, Objective, Assessment, Plan)."""
        
        prompt = f"""Convert the following audio transcription into a professional, structured medical note.

Transcription:
{transcription_text}

Generate a well-formatted medical note with:
- Chief Complaint
- History of Present Illness
- Review of Systems
- Physical Examination
- Assessment and Plan

Be professional, accurate, and maintain medical terminology. If information is unclear, note it appropriately."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.3)
        
        if result:
            return result.strip()
        else:
            # Fallback: Return formatted transcription
            return f"""MEDICAL NOTE

Chief Complaint:
As per audio transcription.

History of Present Illness:
{transcription_text[:500]}...

Assessment and Plan:
To be determined based on clinical findings.

---
Note: This is a preliminary note generated from audio transcription. Please review and complete with additional clinical information as needed."""
    
    def suggest_icd10_codes_enhanced(self, medical_note: str, transcription_text: str) -> List[Dict[str, Any]]:
        """
        Sugiere códigos ICD-10 con nivel de confianza y advertencias de documentación faltante
        
        Args:
            medical_note: Nota médica generada
            transcription_text: Transcripción original
            
        Returns:
            Lista de códigos ICD-10 con confidence y missing_documentation_warnings
        """
        system_instruction = """You are a medical coding expert specializing in ICD-10 codes. Return only valid JSON arrays with no additional text."""
        
        prompt = f"""Analyze the following medical note and suggest the most appropriate ICD-10 codes with confidence levels and documentation warnings.

Medical Note:
{medical_note[:1000]}

Original Transcription:
{transcription_text[:500]}

Provide up to 5 ICD-10 codes in JSON format:
[
  {{
    "code": "ICD10_CODE",
    "description": "Full description of the condition",
    "confidence": 0.95,
    "confidence_level": "High|Medium|Low",
    "missing_documentation_warnings": ["Specific missing element 1", "Specific missing element 2"]
  }}
]

Confidence levels:
- High: Strong evidence in documentation
- Medium: Some evidence but could be more specific
- Low: Limited evidence, documentation may be insufficient

Return ONLY valid JSON array, no additional text or markdown."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.2)
        
        if result:
            try:
                result = result.strip()
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                start_idx = result.find("[")
                end_idx = result.rfind("]") + 1
                if start_idx != -1 and end_idx > start_idx:
                    result = result[start_idx:end_idx]
                
                codes = json.loads(result)
                if isinstance(codes, list):
                    valid_codes = []
                    for code in codes[:5]:
                        if isinstance(code, dict) and "code" in code:
                            confidence = float(code.get("confidence", 0.7))
                            if confidence >= 0.8:
                                conf_level = "High"
                            elif confidence >= 0.5:
                                conf_level = "Medium"
                            else:
                                conf_level = "Low"
                            
                            valid_codes.append({
                                "code": str(code.get("code", "")),
                                "description": str(code.get("description", "")),
                                "confidence": confidence,
                                "confidence_level": code.get("confidence_level", conf_level),
                                "missing_documentation_warnings": code.get("missing_documentation_warnings", [])
                            })
                    if valid_codes:
                        return valid_codes
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing ICD-10 codes JSON: {e}")
        
        # Fallback
        return [
            {
                "code": "Z00.00",
                "description": "Encounter for general adult medical examination without abnormal findings",
                "confidence": 0.7,
                "confidence_level": "Medium",
                "missing_documentation_warnings": []
            }
        ]
    
    def suggest_icd10_codes(self, medical_note: str, transcription_text: str) -> List[Dict[str, Any]]:
        """
        Suggest ICD-10 codes based on medical note and transcription
        
        Args:
            medical_note: The generated medical note
            transcription_text: Original transcription
            
        Returns:
            List of ICD-10 code suggestions with descriptions and confidence
        """
        system_instruction = """You are a medical coding expert specializing in ICD-10 codes. Return only valid JSON arrays with no additional text."""
        
        prompt = f"""Analyze the following medical note and suggest the most appropriate ICD-10 codes.

Medical Note:
{medical_note[:1000]}

Original Transcription:
{transcription_text[:500]}

Provide up to 5 ICD-10 codes in JSON format:
[
  {{
    "code": "ICD10_CODE",
    "description": "Full description of the condition",
    "confidence": 0.95
  }}
]

Return ONLY valid JSON array, no additional text or markdown."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.2)
        
        if result:
            try:
                # Try to extract JSON from response
                result = result.strip()
                # Remove markdown code blocks if present
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                # Try to find JSON array in the response
                start_idx = result.find("[")
                end_idx = result.rfind("]") + 1
                if start_idx != -1 and end_idx > start_idx:
                    result = result[start_idx:end_idx]
                
                codes = json.loads(result)
                if isinstance(codes, list):
                    # Validate and clean codes
                    valid_codes = []
                    for code in codes[:5]:
                        if isinstance(code, dict) and "code" in code:
                            valid_codes.append({
                                "code": str(code.get("code", "")),
                                "description": str(code.get("description", "")),
                                "confidence": float(code.get("confidence", 0.7))
                            })
                    if valid_codes:
                        return valid_codes
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing ICD-10 codes JSON: {e}")
                logger.debug(f"Response was: {result}")
        
        # Fallback: Return example codes
        return [
            {
                "code": "Z00.00",
                "description": "Encounter for general adult medical examination without abnormal findings",
                "confidence": 0.7
            }
        ]
    
    def suggest_cpt_codes_enhanced(self, medical_note: str, transcription_text: str) -> List[Dict[str, Any]]:
        """
        Sugiere códigos CPT con nivel de confianza y advertencias de documentación faltante
        
        Args:
            medical_note: Nota médica generada
            transcription_text: Transcripción original
            
        Returns:
            Lista de códigos CPT con confidence y missing_documentation_warnings
        """
        system_instruction = """You are a medical coding expert specializing in CPT codes and modifiers. Return only valid JSON arrays with no additional text."""
        
        prompt = f"""Analyze the following medical note and suggest appropriate CPT codes with modifiers, confidence levels, and documentation warnings.

Medical Note:
{medical_note[:1000]}

Original Transcription:
{transcription_text[:500]}

Provide up to 5 CPT codes in JSON format:
[
  {{
    "code": "CPT_CODE",
    "description": "Description of the procedure/service",
    "modifier": "25 or null if not applicable",
    "confidence": 0.95,
    "confidence_level": "High|Medium|Low",
    "missing_documentation_warnings": ["Specific missing element 1"]
  }}
]

Confidence levels:
- High: Strong evidence in documentation
- Medium: Some evidence but could be more specific
- Low: Limited evidence, documentation may be insufficient

Return ONLY valid JSON array, no additional text or markdown."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.2)
        
        if result:
            try:
                result = result.strip()
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                start_idx = result.find("[")
                end_idx = result.rfind("]") + 1
                if start_idx != -1 and end_idx > start_idx:
                    result = result[start_idx:end_idx]
                
                codes = json.loads(result)
                if isinstance(codes, list):
                    valid_codes = []
                    for code in codes[:5]:
                        if isinstance(code, dict) and "code" in code:
                            confidence = float(code.get("confidence", 0.7))
                            if confidence >= 0.8:
                                conf_level = "High"
                            elif confidence >= 0.5:
                                conf_level = "Medium"
                            else:
                                conf_level = "Low"
                            
                            valid_codes.append({
                                "code": str(code.get("code", "")),
                                "description": str(code.get("description", "")),
                                "modifier": code.get("modifier") if code.get("modifier") else None,
                                "confidence": confidence,
                                "confidence_level": conf_level,
                                "missing_documentation_warnings": code.get("missing_documentation_warnings", [])
                            })
                    if valid_codes:
                        return valid_codes
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing CPT codes JSON: {e}")
        
        # Fallback
        return [
            {
                "code": "99213",
                "description": "Office or other outpatient visit for the evaluation and management of an established patient",
                "modifier": "25",
                "confidence": 0.7,
                "confidence_level": "Medium",
                "missing_documentation_warnings": []
            }
        ]
    
    def suggest_cpt_codes(self, medical_note: str, transcription_text: str) -> List[Dict[str, Any]]:
        """
        Suggest CPT codes with modifiers based on medical note
        
        Args:
            medical_note: The generated medical note
            transcription_text: Original transcription
            
        Returns:
            List of CPT code suggestions with modifiers and confidence
        """
        system_instruction = """You are a medical coding expert specializing in CPT codes and modifiers. Return only valid JSON arrays with no additional text."""
        
        prompt = f"""Analyze the following medical note and suggest appropriate CPT codes with modifiers.

Medical Note:
{medical_note[:1000]}

Original Transcription:
{transcription_text[:500]}

Provide up to 5 CPT codes in JSON format:
[
  {{
    "code": "CPT_CODE",
    "description": "Description of the procedure/service",
    "modifier": "25 or null if not applicable",
    "confidence": 0.95
  }}
]

Common modifiers:
- 25: Significant, separately identifiable evaluation and management service
- 59: Distinct procedural service
- 26: Professional component
- TC: Technical component

Return ONLY valid JSON array, no additional text or markdown."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.2)
        
        if result:
            try:
                # Try to extract JSON from response
                result = result.strip()
                # Remove markdown code blocks if present
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                # Try to find JSON array in the response
                start_idx = result.find("[")
                end_idx = result.rfind("]") + 1
                if start_idx != -1 and end_idx > start_idx:
                    result = result[start_idx:end_idx]
                
                codes = json.loads(result)
                if isinstance(codes, list):
                    # Validate and clean codes
                    valid_codes = []
                    for code in codes[:5]:
                        if isinstance(code, dict) and "code" in code:
                            valid_codes.append({
                                "code": str(code.get("code", "")),
                                "description": str(code.get("description", "")),
                                "modifier": code.get("modifier") if code.get("modifier") else None,
                                "confidence": float(code.get("confidence", 0.7))
                            })
                    if valid_codes:
                        return valid_codes
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing CPT codes JSON: {e}")
                logger.debug(f"Response was: {result}")
        
        # Fallback: Return example codes
        return [
            {
                "code": "99213",
                "description": "Office or other outpatient visit for the evaluation and management of an established patient",
                "modifier": "25",
                "confidence": 0.7
            }
        ]
    
    def generate_cms1500_form_data(
        self,
        medical_note: str,
        icd10_codes: List[Dict[str, Any]],
        cpt_codes: List[Dict[str, Any]],
        patient_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate CMS-1500 form data structure
        
        Args:
            medical_note: Generated medical note
            icd10_codes: Suggested ICD-10 codes
            cpt_codes: Suggested CPT codes with modifiers
            patient_info: Optional patient information
            
        Returns:
            CMS-1500 form data as JSON
        """
        # Extract primary diagnosis from ICD-10 codes
        primary_diagnosis = icd10_codes[0] if icd10_codes else {"code": "", "description": ""}
        
        # Build form data structure
        form_data = {
            # Patient Information (Box 1-13)
            "patient_name": patient_info.get("name", "") if patient_info else "",
            "patient_dob": patient_info.get("dob", "") if patient_info else "",
            "patient_sex": patient_info.get("sex", "") if patient_info else "",
            "patient_address": patient_info.get("address", "") if patient_info else "",
            "patient_city_state_zip": patient_info.get("city_state_zip", "") if patient_info else "",
            "patient_phone": patient_info.get("phone", "") if patient_info else "",
            "patient_id": patient_info.get("id", "") if patient_info else "",
            
            # Insurance Information (Box 14-33)
            "insured_name": patient_info.get("insured_name", "") if patient_info else "",
            "insured_id": patient_info.get("insured_id", "") if patient_info else "",
            "insurance_group": patient_info.get("insurance_group", "") if patient_info else "",
            
            # Diagnosis Codes (Box 21)
            "diagnosis_codes": [code["code"] for code in icd10_codes[:4]],  # CMS-1500 allows up to 4 diagnosis codes
            "primary_diagnosis": primary_diagnosis["code"],
            
            # Procedure Codes (Box 24)
            "procedures": [
                {
                    "cpt_code": code["code"],
                    "modifier": code.get("modifier", ""),
                    "diagnosis_pointer": "1",  # Points to primary diagnosis
                    "charges": "",  # To be filled by billing
                    "days": "1",
                    "description": code["description"]
                }
                for code in cpt_codes
            ],
            
            # Service Dates (Box 24A)
            "service_date": "",  # To be filled
            
            # Provider Information
            "provider_npi": "",  # To be filled
            "provider_name": "",
            "provider_address": "",
            "provider_tax_id": "",
            
            # Additional Information
            "rendering_provider": "",
            "billing_provider": "",
            "facility_name": "",
            
            # Notes
            "notes": medical_note[:500],  # Truncated for form
            
            # Metadata
            "form_version": "02/12",
            "generated_at": "",
        }
        
        return form_data
    
    def run_full_workflow(self, transcription_text: str, patient_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the complete medical workflow:
        1. Generate medical note
        2. Suggest ICD-10 codes
        3. Suggest CPT codes
        4. Generate CMS-1500 form
        
        Args:
            transcription_text: The transcribed audio text
            patient_info: Optional patient information
            
        Returns:
            Dictionary with all workflow results
        """
        logger.info("Starting full medical workflow with Gemini...")
        
        # Step 1: Generate medical note
        logger.info("Step 1: Generating medical note...")
        medical_note = self.generate_medical_note(transcription_text)
        
        # Step 2: Suggest ICD-10 codes
        logger.info("Step 2: Suggesting ICD-10 codes...")
        icd10_codes = self.suggest_icd10_codes(medical_note, transcription_text)
        
        # Step 3: Suggest CPT codes
        logger.info("Step 3: Suggesting CPT codes...")
        cpt_codes = self.suggest_cpt_codes(medical_note, transcription_text)
        
        # Step 4: Generate CMS-1500 form
        logger.info("Step 4: Generating CMS-1500 form...")
        cms1500_form = self.generate_cms1500_form_data(medical_note, icd10_codes, cpt_codes, patient_info)
        
        logger.info("Medical workflow completed successfully")
        
        return {
            "medical_note": medical_note,
            "icd10_codes": icd10_codes,
            "cpt_codes": cpt_codes,
            "cms1500_form_data": cms1500_form,
            "workflow_status": "form_created"
        }
    
    def generate_patient_summary(self, medical_note: str, transcription_text: str) -> str:
        """
        Genera un resumen de visita en lenguaje simple para pacientes
        
        Args:
            medical_note: Nota médica generada
            transcription_text: Transcripción original
            
        Returns:
            Resumen en lenguaje simple
        """
        system_instruction = """You are a medical communication expert. Generate patient-friendly visit summaries in plain language, avoiding complex medical jargon."""
        
        prompt = f"""Convert the following medical note into a clear, patient-friendly summary in Spanish.

Medical Note:
{medical_note[:1500]}

Generate a summary that includes:
1. Reason for visit (in simple terms)
2. Findings (what was observed)
3. Diagnosis (simplified language)
4. Next steps (what happens next)

Use clear, simple language that a patient can understand. Avoid medical jargon. If you must use medical terms, explain them simply.

Return the summary in Spanish."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.4)
        
        if result:
            return result.strip()
        
        # Fallback
        return f"""Resumen de la Visita

Motivo de la consulta:
Según la transcripción de audio.

Hallazgos:
Se realizó una evaluación médica. Por favor, consulte con su médico para más detalles.

Próximos pasos:
Siga las indicaciones de su médico y programe un seguimiento según sea necesario."""
    
    def generate_next_steps(self, medical_note: str, transcription_text: str) -> List[Dict[str, Any]]:
        """
        Genera una lista clara de próximos pasos para el paciente
        
        Args:
            medical_note: Nota médica generada
            transcription_text: Transcripción original
            
        Returns:
            Lista de próximos pasos: [{type: "medication|lab|followup", description: "...", details: "..."}, ...]
        """
        system_instruction = """You are a medical communication expert. Extract and format next steps from clinical notes into a clear checklist for patients."""
        
        prompt = f"""Extract next steps from the following medical note and format them as a clear checklist.

Medical Note:
{medical_note[:1500]}

Return ONLY valid JSON array:
[
  {{
    "type": "medication|lab|followup|lifestyle|referral",
    "description": "Clear description of what to do",
    "details": "Additional details (how, when, why)",
    "priority": "high|medium|low"
  }}
]

Return ONLY valid JSON array, no additional text."""
        
        result = self._call_gemini(prompt, system_instruction, temperature=0.3)
        
        if result:
            try:
                result = result.strip()
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()
                
                start_idx = result.find("[")
                end_idx = result.rfind("]") + 1
                if start_idx != -1 and end_idx > start_idx:
                    result = result[start_idx:end_idx]
                
                steps = json.loads(result)
                if isinstance(steps, list):
                    return steps
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing next steps JSON: {e}")
        
        return []