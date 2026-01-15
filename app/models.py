from enum import Enum
from sqlmodel import SQLModel, Field


class ProcessingStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class TaskBase(SQLModel):
    status: ProcessingStatus = Field(
        default=ProcessingStatus.pending, 
        index=True
    )
    
    processed_text: str | None = Field(
        default=None,
        nullable=True,
    )

    error_message: str | None = Field(
        default=None,
        nullable=True,
    )


class Task(TaskBase, table=True):
    id: int | None = Field(
        default=None,
        primary_key=True
    )


class TaskPublic(TaskBase):
    id: int


class TaskCreate(SQLModel):
    status: ProcessingStatus = ProcessingStatus.pending


class TaskUpdate(SQLModel):
    status: ProcessingStatus
    processed_text: str | None = None
    error_message: str | None = None