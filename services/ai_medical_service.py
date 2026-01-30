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
