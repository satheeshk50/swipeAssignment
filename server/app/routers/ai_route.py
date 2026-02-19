import logging
from typing import Dict, Any, List

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
                result = await _ai_service.generate(
                    system_prompt=INVOICE_EXTRACTION_PROMPT,
                    image_paths=[file_path],
                    response_schema=SingleInvoiceExtraction,
                )

                if hasattr(result, "model_dump"):
                    data = result.model_dump(mode="json")
                elif isinstance(result, dict):
                    data = result
                else:
                    data = dict(result)

                results.append(data)

            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {e}")
                results.append({"error": str(e), "file": Path(file_path).name})

        return results

    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        raise



def _write_file(path: Path, content: bytes):
    """Sync file write helper for asyncio.to_thread"""
    with open(path, "wb") as f:
        f.write(content)


@router.post("/extract")
async def process_invoice(files: List[UploadFile] = File(...)):
    try:
        # returns List[Dict[str, Any]] or List[SingleInvoiceExtraction] (as dicts)
        invoice_data = await process_invoice_with_ai(files)
        return invoice_data
    except Exception as e:
        logger.error(f"Error processing invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))