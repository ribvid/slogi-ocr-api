from fastapi import FastAPI, File, UploadFile, HTTPException
from pathlib import Path
import shutil
import tempfile
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered


app = FastAPI()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/process-with-marker")
async def process_with_marker(file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()

    try:
        # Save uploaded file to temp directory
        temp_pdf_path = Path(temp_dir) / file.filename
        
        with open(temp_pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        config = {
            "--output_format": "markdown",
            "--disable_image_extraction": True,
            "--extract_images": False,
            "--disable_ocr": True,
            "--disable_ocr_math": True,
            "--force_ocr": True,
            "--strip_existing_ocr": True,
        }
        
        config_parser = ConfigParser(config)

        converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
        )

        rendered = converter(str(temp_pdf_path))
        
        text, _, _ = text_from_rendered(rendered)
        
        # Return the ZIP file
        return {"result": text}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )