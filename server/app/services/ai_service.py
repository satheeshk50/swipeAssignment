import asyncio
import logging
import os
import pandas as pd
import json
import time
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import UploadFile
from google import genai
# from google.cloud import vision
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from google.genai import types

from app.models.output_schema import SingleInvoiceExtraction
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

class AIService:
    """
    Unified Service for interacting with Google Cloud Vision (OCR) and Google Gemini AI.
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             logger.warning("GEMINI_API_KEY not found in environment variables.")
        
        self.genai_client = genai.Client(api_key=api_key)
        
        self.model_name = "gemini-2.5-flash" 


        self.azure_client = DocumentIntelligenceClient(
                endpoint=endpoint, 
                credential=AzureKeyCredential(key)
            )
                


    async def _extract_text_with_Azure_Intelligence(self, image_path: str) -> Dict[str, str]:
        """
        Asynchronously extracts text from images using Google Cloud Vision.
        Returns a dictionary mapping filename -> extracted text.
        """
        if not image_path or image_path == "":
            return ""
        
        logger.info(f"Extracting text from {image_path} with Azure Intelligence")
        extracted_text_dict = {}

        file_ext = Path(image_path).suffix.lower()
        if file_ext in ['.xlsx', '.xls']:
            model_id = "prebuilt-layout" # Supports Excel
        else:
            model_id = "prebuilt-receipt"
            
        with open(image_path, "rb") as f:
            poller = self.azure_client.begin_analyze_document(
            model_id=model_id, 
            body=f  # Required named parameter for file bytes
        )   
        result = poller.result()
        return result.content

    async def generate(
            self,
            system_prompt: str,
            image_path: str,
            response_schema: Any
        ) -> Dict[str, Any]:
        """
        Upload files and call Gemini with text + images.
        """

        logger.info(f"Uploading {image_path} document to Gemini...")

        # 1️⃣ Upload files concurrently (non-blocking)
        async def upload_one(path: str):
            if not Path(path).exists():
                return None
            
            upload_path = path

            # Gemini doesn't natively parse .xlsx headers cleanly via File API visually sometimes.
            # Convert Excel to CSV as a temporary file to give it pure text data.
            file_ext = Path(path).suffix.lower()
            temp_txt_path = None
            if file_ext in ['.xlsx', '.xls']:
                try:
                    logger.info(f"Converting Excel file {path} to text for Gemini...")
                    df = await asyncio.to_thread(pd.read_excel, path)
                    
                    # Create a temporary file to hold the CSV text, suffix .txt bypasses Windows mime errors
                    temp_txt = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
                    temp_txt_path = temp_txt.name
                    temp_txt.close()
                    
                    # Write CSV
                    await asyncio.to_thread(df.to_csv, temp_txt_path, index=False)
                    upload_path = temp_txt_path
                except Exception as e:
                    logger.error(f"Failed to convert Excel to text: {e}")
                    # Fallback to uploading raw excel if conversion fails
                    upload_path = path

            try:
                uploaded = await asyncio.to_thread(
                    self.genai_client.files.upload,
                    file=upload_path
                )
                
                # Cleanup the temp TXT if we created one
                if temp_txt_path and os.path.exists(temp_txt_path):
                    os.remove(temp_txt_path)
                    
                return uploaded
            except Exception as e:
                logger.error(f"Upload failed for {upload_path}: {e}")
                if temp_txt_path and os.path.exists(temp_txt_path):
                    os.remove(temp_txt_path)
                return None

        uploaded_file = await upload_one(image_path)

        uploaded_files = [uploaded_file] if uploaded_file else []
        file_names_to_delete = [f.name for f in uploaded_files]


        try:
            # 2️⃣ Prepare contents
            contents = [system_prompt, *uploaded_files]

            logger.info(f"Calling Gemini model {self.model_name}")

            # 3️⃣ Run blocking model call inside thread + timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        temperature=0.3,
                    )
                ),
                timeout=300.0
            )

            print(response)
            return response.parsed

        except Exception as e:
            logger.warning(f"OCR model failed: {e}")
            raise

        finally:
            if file_names_to_delete:
                await self.delete_uploaded_files(file_names_to_delete)


    async def delete_uploaded_files(self, file_names: List[str]):
        """
        Deletes files from Google Cloud storage using their resource names.
        """
        logger.info(f"Cleaning up {len(file_names)} files from Gemini servers...")
        
        async def delete_one(file_name):
            try:
                await asyncio.to_thread(self.genai_client.files.delete, name=file_name)
                logger.debug(f"Successfully deleted: {file_name}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_name}: {e}")

        await asyncio.gather(*(delete_one(name) for name in file_names))

    