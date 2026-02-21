import logging
from typing import Dict, Any, List
import asyncio
import time
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.ai_service import AIService
from app.models.output_schema import SingleInvoiceExtraction
from app.routers.prompts import INVOICE_EXTRACTION_PROMPT
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)

router = APIRouter()

_ai_service = AIService()


async def process_invoice_with_ai(files: List[UploadFile], fast_mode: bool = False) -> List[Dict[str, Any]]:
    """
    Process multiple uploaded invoice files sequentially.
    1. Saves files to 'app/uploaded_files/{timestamp}/{filename}'
    2. Processes each file individually with Gemini
    3. Returns a list of extracted data objects
    """
    total_start_time = time.time()

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
                azure_result = ""
                if not fast_mode:
                    print("\n🔍 Step 1: Extracting raw text using azure document Intelligence API...")
                    azure_start_time = time.time()
                    azure_result = (await _ai_service._extract_text_with_Azure_Intelligence(
                        image_path=str(file_path))
                    )
                    azure_end_time = time.time()
                    print(f"⏱️ Azure Document Intelligence time taken: {azure_end_time - azure_start_time:.2f} seconds")
                    if azure_result:
                        print(f"✅ Document Intelligence extraction successful! Text length: {azure_result} chars.")

                    else:
                        print("⚠️ Document Intelligence extraction returned no text.")
                else:
                    print("\n⚡ Fast Mode Enabled: Skipping Document Intelligence extraction.")
                
            except Exception as e:
                logger.error(f"❌ Failed to process file with Document Intelligence: {e}")
                print("⚠️ Falling back to Gemini LLM alone due to Document Intelligence failure.")
                
            try:
                dynamic_prompt = INVOICE_EXTRACTION_PROMPT
                if azure_result:
                    dynamic_prompt += f"""

                    <input_data>
                    [INSERT EXCEL/PDF/IMAGE TEXT OR FILE PAYLOAD HERE]

                    The following text was extracted using azure document Intelligence API.
                    If there are any differences between your own extraction and this text,
                    prioritize the Document Intelligence extracted data for better accuracy.

                    Document Intelligence Extracted Text:
                    \"\"\"{azure_result}\"\"\"
                    </input_data>

                    """
                else:
                    dynamic_prompt += """

                    <input_data>
                    [INSERT EXCEL/PDF/IMAGE TEXT OR FILE PAYLOAD HERE]
                    </input_data>

                    """
                    
                print("🤖 Step 2: Generating structured JSON using Gemini LLM...")
                gemini_start_time = time.time()
                result = await _ai_service.generate(
                    system_prompt=dynamic_prompt,
                    image_path=str(file_path),
                    response_schema=SingleInvoiceExtraction,
                )
                gemini_end_time = time.time()
                print(f"⏱️ Gemini 2.5 Flash time taken: {gemini_end_time - gemini_start_time:.2f} seconds")
                print("✅ Gemini generation successful!")

                print("🛠️ Step 3: Parsing and formatting output...")
                if hasattr(result, "model_dump"):
                    data = result.model_dump(mode="json")
                elif isinstance(result, dict):
                    data = result
                else:
                    data = dict(result)
                    
                # Save the output to a text file
                output_txt_path = base_dir / f"{file.filename}_output.txt"
                output_str = json.dumps(data, indent=4)
                await asyncio.to_thread(_write_file, output_txt_path, output_str.encode('utf-8'))
                print(f"📄 Saved extracted output to: {output_txt_path}")

                results.append(data)
                print("🎉 Successfully processed and appended to batch results!\n")

            except Exception as e:
                logger.error(f"❌ Failed during LLM generation or parsing: {e}")
                results.append({"error": str(e), "file": Path(file_path).name})

        total_end_time = time.time()
        print(f"🏁 Finished processing all {len(saved_file_paths)} files in {total_end_time - total_start_time:.2f} seconds. Returning results to client.")
        return results

    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



def _write_file(path: Path, content: bytes):
    """Sync file write helper for asyncio.to_thread"""
    with open(path, "wb") as f:
        f.write(content)


from fastapi import Form

from fastapi import Request

@router.post("/extract")
async def process_invoice(
    # request: Request,
    files: List[UploadFile] = File(...),
    fast_mode: str = Form("false")
):
    try:
        # form_data = await request.form()
        # print("--- RAW FORM DATA ---")
        # for key, value in form_data.items():
        #     print(f"{key}: {value} (Type: {type(value)})")
        # print("---------------------")

        is_fast = fast_mode.lower() == "true"
        print(f"Fast mode parsed value: {is_fast} and the {type(is_fast)}")
        # returns List[Dict[str, Any]] or List[SingleInvoiceExtraction] (as dicts)
        invoice_data = await process_invoice_with_ai(files, is_fast)
        print(f"Invoice data: {invoice_data}")
        return {"message":"Invoice processed successfully", "data":invoice_data,"status_code":200}
    except Exception as e:
        logger.error(f"Error processing invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))