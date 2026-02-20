import logging
from typing import Dict, Any, List
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.ai_service import AIService
from app.models.output_schema import SingleInvoiceExtraction
from app.routers.prompts import INVOICE_EXTRACTION_PROMPT
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)

router = APIRouter()

_ai_service = AIService()


async def process_invoice_with_ai(files: List[UploadFile]) -> List[Dict[str, Any]]:
    """
    Process multiple uploaded invoice files sequentially.
    1. Saves files to 'app/uploaded_files/{timestamp}/{filename}'
    2. Processes each file individually with Gemini
    3. Returns a list of extracted data objects
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(__file__).parent.parent / "uploaded_files" / timestamp

    # Offload directory creation (minor, but clean)
    await asyncio.to_thread(base_dir.mkdir, parents=True, exist_ok=True)

    saved_file_paths = []

    try:
        for file in files:
            file_path = base_dir / file.filename

            # Read async from UploadFile
            content = await file.read()

            # Write using thread (prevents event-loop blocking)
            await asyncio.to_thread(
                _write_file,
                file_path,
                content
            )

            saved_file_paths.append(str(file_path))
            logger.info(f"Saved file: {file_path}")

        # 2️⃣ Sequential AI processing (your existing logic)
        results = []
        logger.info(f"Starting sequential processing for {len(saved_file_paths)} files...")

        for file_path in saved_file_paths:

            try:
                print("\n🔍 Step 1: Extracting raw text using Google Vision API...")
                vision_result = (await _ai_service._extract_text_with_vision(
                    image_paths=[file_path] or "")
                )
                if vision_result:
                    print(f"✅ Vision extraction successful! Text length: {len(vision_result)} chars.")
                else:
                    print("⚠️ Vision extraction returned no text.")
                
            except Exception as e:
                logger.error(f"❌ Failed to process file with vision: {e}")
                results.append({"error": str(e), "file": Path(file_path).name})
                continue # Skip remaining if vision crashes
                
            try:
                dynamic_prompt = INVOICE_EXTRACTION_PROMPT
                if vision_result:
                    dynamic_prompt += f"""

                    <input_data>
                    [INSERT EXCEL/PDF/IMAGE TEXT OR FILE PAYLOAD HERE]

                    The following text was extracted using Google Cloud Vision.
                    If there are any differences between your own extraction and this text,
                    prioritize the Vision-extracted data for better accuracy.

                    Vision Extracted Text:
                    \"\"\"{vision_result}\"\"\"
                    </input_data>

                    """
                else:
                    dynamic_prompt += """

                    <input_data>
                    [INSERT EXCEL/PDF/IMAGE TEXT OR FILE PAYLOAD HERE]
                    </input_data>

                    """
                    
                print("🤖 Step 2: Generating structured JSON using Gemini LLM...")
                result = await _ai_service.generate(
                    system_prompt=dynamic_prompt,
                    image_paths=[file_path],
                    response_schema=SingleInvoiceExtraction,
                )
                print("✅ Gemini generation successful!")

                print("🛠️ Step 3: Parsing and formatting output...")
                if hasattr(result, "model_dump"):
                    data = result.model_dump(mode="json")
                elif isinstance(result, dict):
                    data = result
                else:
                    data = dict(result)

                results.append(data)
                print("🎉 Successfully processed and appended to batch results!\n")

            except Exception as e:
                logger.error(f"❌ Failed during LLM generation or parsing: {e}")
                results.append({"error": str(e), "file": Path(file_path).name})

        print(f"🏁 Finished processing all {len(saved_file_paths)} files. Returning results to client.")
        return results

    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



def _write_file(path: Path, content: bytes):
    """Sync file write helper for asyncio.to_thread"""
    with open(path, "wb") as f:
        f.write(content)


@router.post("/extract")
async def process_invoice(files: List[UploadFile] = File(...)):
    try:
        # returns List[Dict[str, Any]] or List[SingleInvoiceExtraction] (as dicts)
        invoice_data = await process_invoice_with_ai(files)
        return {"message":"Invoice processed successfully", "data":invoice_data,"status_code":200}
    except Exception as e:
        logger.error(f"Error processing invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))