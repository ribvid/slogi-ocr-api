from pathlib import Path
import shutil
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from sqlmodel import Session
from db import engine
from models import Task, ProcessingStatus


def process_file_with_marker(task_id: int, temp_file_path: str) -> None:
    """Process file with marker - RQ worker function"""
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