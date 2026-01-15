from typing import Annotated
from fastapi import Depends, FastAPI, UploadFile, HTTPException, BackgroundTasks
from pathlib import Path
import shutil
import tempfile
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from sqlmodel import Session
from db import engine, create_db_and_tables, get_session
from models import Task, TaskPublic, ProcessingStatus


MAX_FILE_SIZE = 10 * 1024 * 1024 # Maximum file size (10 MB)


SessionDep = Annotated[Session, Depends(get_session)]


app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


def process_file_with_marker(
    task_id: int,
    temp_file_path: str,
) -> None:
    """Process file with marker in background"""
    with Session(engine) as session:
        task = session.get(Task, task_id)

        temp_dir = Path(temp_file_path).parent

        if not task:
            # Clean up temp file if task not found
            temp_dir.unlink(missing_ok=True)
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



@app.post("/process-with-marker", response_model=TaskPublic, status_code=202)
async def start_processing_with_marker(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    session: SessionDep,
):
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.1f} MB"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    temp_dir = tempfile.mkdtemp()

    try:
        safe_filename = Path(file.filename).name
        temp_file_path = Path(temp_dir) / safe_filename
        
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        task = Task(
            status=ProcessingStatus.pending,
        )
        
        session.add(task)
        session.commit()
        session.refresh(task)

        # Add background processing task
        background_tasks.add_task(
            process_file_with_marker,
            task.id,
            str(temp_file_path),
        )

        return TaskPublic(
            id=task.id,
            status=task.status,
            processed_text=task.processed_text,
            error_message=task.error_message,
        )
        
    except Exception as e:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )
    

@app.get("/status/{task_id}", response_model=TaskPublic)
def get_task_status(
    task_id: int,
    session: SessionDep,
):
    task = session.get(Task, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskPublic(
            id=task.id,
            status=task.status,
            processed_text=task.processed_text,
            error_message=task.error_message,
        )
    
    