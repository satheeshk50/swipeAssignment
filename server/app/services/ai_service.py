import asyncio
import logging
import os
import json
import time
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import UploadFile
from google import genai
from google.cloud import vision
from google.genai import types

from app.models.output_schema import SingleInvoiceExtraction
# from app.routers.prompts import INVOICE_EXTRACTION_PROMPT
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class AIService:
    """
    Unified Service for interacting with Google Cloud Vision (OCR) and Google Gemini AI.
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             logger.warning("GEMINI_API_KEY not found in environment variables.")
        
        self.client = genai.Client(api_key=api_key)
        
        self.model_name = "gemini-2.5-pro" 


        self.vision_client = vision.ImageAnnotatorClient()
        


    async def _extract_text_with_vision(self, image_paths: List[str]) -> Dict[str, str]:
        """
        Asynchronously extracts text from images using Google Cloud Vision.
        Returns a dictionary mapping filename -> extracted text.
        """
        logger.info(f"Extracting text from {len(image_paths)} images with Google Cloud Vision")
        extracted_text_dict = {}

        async def process_image(path: str) -> None:
            if not Path(path).exists():
                logger.warning(f"Image file not found: {path}. Skipping.")
                return

            try:
                def read_file(p):
                    with open(p, "rb") as image_file:
                        return image_file.read()
                
                content = await asyncio.to_thread(read_file, path)
                image = vision.Image(content=content)

                response = await asyncio.to_thread(self.vision_client.document_text_detection, image=image)

                filename = Path(path).name
                if response.text_annotations:
                    extracted_text_dict[filename] = response.text_annotations[0].description
                else:
                    extracted_text_dict[filename] = ""
            except Exception as e:
                logger.error(f"Error extracting text from {path}: {e}")
                filename = Path(path).name
                extracted_text_dict[filename] = ""

        await asyncio.gather(*(process_image(path) for path in image_paths))

        logger.info("OCR extraction completed.")
        return extracted_text_dict

    async def generate(
            self,
            system_prompt: str,
            image_paths: List[str],
            response_schema: Any
        ) -> Dict[str, Any]:
        """
        Upload files and call Gemini with text + images.
        """

        logger.info(f"Uploading {len(image_paths)} documents to Gemini...")

        # 1️⃣ Upload files concurrently (non-blocking)
        async def upload_one(path: str):
            if not Path(path).exists():
                return None
            try:
                return await asyncio.to_thread(
                    self.client.files.upload,
                    file=path
                )
            except Exception as e:
                logger.error(f"Upload failed for {path}: {e}")
                return None

        results = await asyncio.gather(
            *(upload_one(p) for p in image_paths)
        )

        uploaded_files = [r for r in results if r is not None]
        file_names_to_delete = [f.name for f in uploaded_files]


        try:
            # 2️⃣ Prepare contents
            contents = [system_prompt, *uploaded_files]

            logger.info(f"Calling Gemini model {self.model_name}")

            # 3️⃣ Run blocking model call inside thread + timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.models.generate_content,
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
                await asyncio.to_thread(self.client.files.delete, name=file_name)
                logger.debug(f"Successfully deleted: {file_name}")
            except Exception as e:
                logger.error(f"Failed to delete file {file_name}: {e}")

        await asyncio.gather(*(delete_one(name) for name in file_names))

    