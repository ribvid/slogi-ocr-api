from pathlib import Path
import shutil
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from pdf2image import convert_from_path
import pytesseract
from sqlmodel import Session
from db import engine
from models import Task, ProcessingStatus


def process_file_with_marker(task_id: int, temp_file_path: str) -> None:
    """Process file with marker"""
    with Session(engine) as session:
        task = session.get(Task, task_id)
        
        temp_dir = Path(temp_file_path).parent
        
        if not task:
            # Clean up temp file if task not found
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
        
        try:
            config = {
                "--output_format": "markdown",
                "--disable_image_extraction": True,
                "--extract_images": False,
                "--force_ocr": True,
                "--strip_existing_ocr": True,
            }
            
            config_parser = ConfigParser(config)
            
            converter = PdfConverter(
                config=config_parser.generate_config_dict(),
                artifact_dict=create_model_dict(),
            )
            
            rendered = converter(temp_file_path)
            
            text, _, _ = text_from_rendered(rendered)
            
            task.processed_text = text
            task.status = ProcessingStatus.completed
            
            session.add(task)
            session.commit()
        
        except Exception as e:
            task.status = ProcessingStatus.failed
            task.error_message = str(e)
            
            session.add(task)
            session.commit()
        
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)


def process_file_with_tesseract(task_id: int, temp_file_path: str) -> None:
    """Process file with Tesseract"""
    with Session(engine) as session:
        task = session.get(Task, task_id)
        temp_dir = Path(temp_file_path).parent
        
        if not task:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
        
        try:
            # Determine file type
            file_path = Path(temp_file_path)
            file_extension = file_path.suffix.lower()

            # Convert PDF pages to images or load image directly
            if file_extension == '.pdf':
                images = convert_from_path(temp_file_path, dpi=300)
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
                # Load image directly
                from PIL import Image
                images = [Image.open(temp_file_path)]
            else:
                # Unsupported file type
                task.status = ProcessingStatus.failed
                task.error_message = f"Unsupported file type: {file_extension}"
                session.add(task)
                session.commit()
                return
            
            # OCR each page
            text_pages = []
            for i, image in enumerate(images):
                # Configure Tesseract (optional)
                custom_config = r'--psm 1 -l slv'
                text = pytesseract.image_to_string(image, config=custom_config)
                text_pages.append(text)
            
            # Combine all pages
            full_text = "\n\n---PAGE BREAK---\n\n".join(text_pages)
            
            task.processed_text = full_text
            task.status = ProcessingStatus.completed
            session.add(task)
            session.commit()
            
        except Exception as e:
            task.status = ProcessingStatus.failed
            task.error_message = str(e)
            session.add(task)
            session.commit()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)