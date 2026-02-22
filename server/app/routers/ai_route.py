import logging
import json
from typing import Dict, Any, List
import asyncio
import time
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.ai_service import AIService
from app.models.output_schema import DocumentExtraction
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
                file_ext = Path(file_path).suffix.lower()
                
                # NATIVE EXCEL PIPELINE
                if file_ext in ['.xlsx', '.xls']:
                    from app.services.excel_processor import process_excel_with_ai_mapping
                    excel_extraction = await process_excel_with_ai_mapping(str(file_path), _ai_service)
                    
                    # Save the raw document extraction output to a text file for auditing
                    output_txt_path = base_dir / f"{Path(file_path).name}_output.txt"
                    output_str = json.dumps(excel_extraction, indent=4)
                    await asyncio.to_thread(_write_file, output_txt_path, output_str.encode('utf-8'))
                    print(f"📄 Saved native Excel extracted output to: {output_txt_path}")
                    
                    if "invoices" in excel_extraction and isinstance(excel_extraction["invoices"], list):
                        results.extend(excel_extraction["invoices"])
                        print(f"🎉 Successfully processed and extracted {len(excel_extraction['invoices'])} invoices from {Path(file_path).name}!\n")
                    continue # Skip the rest of the generic OCR/Gemini processing

                # STANDARD IMAGE / PDF PIPELINE
                azure_result = ""
                if not fast_mode:
                    print("\n🔍 Step 1: Extracting raw text using azure document Intelligence API...")
                    azure_start_time = time.time()
                    azure_result = await _ai_service._extract_text_with_Azure_Intelligence(str(file_path))
                    azure_end_time = time.time()
                    print(f"⏱️ Azure time taken: {azure_end_time - azure_start_time:.2f} seconds")
                    print("✅ Azure extraction successful!")

                dynamic_prompt = INVOICE_EXTRACTION_PROMPT
                
                if azure_result:
                    dynamic_prompt += f"""

                    <input_data>
                    This is an image/PDF. 
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
                    
                print(f"📄 Processing file: {file_path}")
                print("🤖 Step 2: Generating structured JSON using Gemini LLM...")
                gemini_start_time = time.time()
                # Get the structured extraction
                result = await _ai_service.generate(
                    system_prompt=dynamic_prompt,
                    image_path=str(file_path),
                    response_schema=DocumentExtraction,
                )
                
                gemini_end_time = time.time()
                print(f"⏱️ Gemini 2.5 Flash time taken: {gemini_end_time - gemini_start_time:.2f} seconds")
                print("✅ Gemini generation successful!")
                print("🛠️ Step 3: Parsing and formatting output...")
                
                # DocumentExtraction model returns a list of invoices
                if hasattr(result, "model_dump"):
                    data = result.model_dump(mode="json")
                elif isinstance(result, dict):
                    data = result
                else:
                    data = json.loads(result.model_dump_json())
                    
                # Save the raw document extraction output to a text file
                output_txt_path = base_dir / f"{Path(file_path).name}_output.txt"
                output_str = json.dumps(data, indent=4)
                await asyncio.to_thread(_write_file, output_txt_path, output_str.encode('utf-8'))
                print(f"📄 Saved extracted output to: {output_txt_path}")

                # The frontend expects a flat list of individual invoice objects.
                # So we extract the aggregated invoices array out of the DocumentExtraction root.
                if "invoices" in data and isinstance(data["invoices"], list):
                    results.extend(data["invoices"])
                    print(f"🎉 Successfully processed and extracted {len(data['invoices'])} invoices from {Path(file_path).name}!\n")
                else:
                     logger.error(f"Failed to find invoices array in output for {Path(file_path).name}")
                     results.append({"error": "Failed to parse aggregated invoices list", "file": Path(file_path).name})

            except Exception as e:
                error_msg = str(e)
                if "429 RESOURCE_EXHAUSTED" in error_msg or "Quota exceeded" in error_msg or '429' in str(getattr(e, 'code', '')):
                    error_msg = "429 RESOURCE_EXHAUSTED: You have exceeded your Gemini API free tier rate limit/quota. Please check your billing details or try again later."
                
                logger.error(f"❌ Failed during LLM generation or parsing: {error_msg}")
                results.append({"error": error_msg, "file": Path(file_path).name})

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
#         invoice_data = [
#   {
#     "invoice_details": {
#       "serial_number": "RAY/23-24/286",
#       "total_quantity": 3.0,
#       "total_tax_amount": 14805.33,
#       "total_amount": 109588.00,
#       "date": "12 Nov 2024"
#     },
#     "customer": {
#       "customer_name": "Shounak",
#       "phone_number": "999999999",
#       "total_purchase_amount": 109588.00
#     },
#     "products": [
#       {
#         "name": "iPHONE 16",
#         "quantity": 1.0,
#         "unit_price": 69183.35,
#         "tax": "18%",
#         "price_with_tax": 79990.00
#       },
#       {
#         "name": "iPHONE 16 Cover",
#         "quantity": 1.0,
#         "unit_price": 3977.68,
#         "tax": "18%",
#         "price_with_tax": 4599.00
#       },
#       {
#         "name": "Beats PRO X",
#         "quantity": 1.0,
#         "unit_price": 21621.64,
#         "tax": "18%",
#         "price_with_tax": 24999.00
#       }
#     ]
#   },
#   {
#     "invoice_details": {
#       "serial_number": "RAY/23-24/285",
#       "total_quantity": 1.0,
#       "total_tax_amount": 0.0,
#       "total_amount": 10000.00,
#       "date": "12 Nov 2024"
#     },
#     "customer": {
#       "customer_name": "Abhinav",
#       "phone_number": "888888888",
#       "total_purchase_amount": 10000.00
#     },
#     "products": [
#       {
#         "name": "SPEAKER",
#         "quantity": 1.0,
#         "unit_price": 10000.00,
#         "tax": "0%",
#         "price_with_tax": 10000.00
#       }
#     ]
#   },
#   {
#     "invoice_details": {
#       "serial_number": "RAY/23-24/284",
#       "total_quantity": 1.0,
#       "total_tax_amount": 0.0,
#       "total_amount": 88.98,
#       "date": "08 Nov 2024"
#     },
#     "customer": {
#       "customer_name": "Ramesh",
#       "phone_number": "777777777",
#       "total_purchase_amount": 88.98
#     },
#     "products": [
#       {
#         "name": "12 MM PLAIN GLASS",
#         "quantity": 1.0,
#         "unit_price": 88.98,
#         "tax": "0%",
#         "price_with_tax": 88.98
#       }
#     ]
#   },
#   {
#     "invoice_details": {
#       "serial_number": "RAY/23-24/282",
#       "total_quantity": 500.0,
#       "total_tax_amount": 0.0,
#       "total_amount": 37.08,
#       "date": "07 Nov 2024"
#     },
#     "customer": {
#       "customer_name": "RAM",
#       "phone_number": "999999999",
#       "total_purchase_amount": 37.08
#     },
#     "products": [
#       {
#         "name": "12 MM PLAIN GLASS",
#         "quantity": 500.0,
#         "unit_price": 0.07,
#         "tax": "0%",
#         "price_with_tax": 37.08
#       }
#     ]
#   },
#   {
#     "invoice_details": {
#       "serial_number": "RAY/23-24/280",
#       "total_quantity": 2.0,
#       "total_tax_amount": 0.0,
#       "total_amount": 105.00,
#       "date": "06 Nov 2024"
#     },
#     "customer": {
#       "customer_name": "Ramesh",
#       "phone_number": "777777777",
#       "total_purchase_amount": 105.00
#     },
#     "products": [
#       {
#         "name": "12 MM PLAIN GLASS",
#         "quantity": 1.0,
#         "unit_price": 105.00,
#         "tax": "18%",
#         "price_with_tax": 105.00
#       },
#       {
#         "name": "plain glass",
#         "quantity": 1.0,
#         "unit_price": 0.00,
#         "tax": "18%",
#         "price_with_tax": 0.00
#       }
#     ]
#   },
#   {
#     "invoice_details": {
#       "serial_number": "RAY/23-24/278",
#       "total_quantity": 1.0,
#       "total_tax_amount": 0.0,
#       "total_amount": 105.00,
#       "date": "05 Nov 2024"
#     },
#     "customer": {
#       "customer_name": "Decathlon",
#       "phone_number": "555555555",
#       "total_purchase_amount": 105.00
#     },
#     "products": [
#       {
#         "name": "12 MM PLAIN GLASS",
#         "quantity": 1.0,
#         "unit_price": 105.00,
#         "tax": "18%",
#         "price_with_tax": 105.00
#       }
#     ]
#   },
#   {
#     "invoice_details": {
#       "serial_number": "RAY/23-24/275",
#       "total_quantity": 100.0,
#       "total_tax_amount": 0.0,
#       "total_amount": 55000.00,
#       "date": "01 Nov 2024"
#     },
#     "customer": {
#       "customer_name": "geeetha",
#       "phone_number": "666666666",
#       "total_purchase_amount": 55000.00
#     },
#     "products": [
#       {
#         "name": "plain glass",
#         "quantity": 100.0,
#         "unit_price": 55000.00,
#         "tax": "18%",
#         "price_with_tax": 590.00
#       }
#     ]
#   }
# ]
        return {"message":"Invoice processed successfully", "data":invoice_data,"status_code":200}
    except Exception as e:
        logger.error(f"Error processing invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))