FROM python:3.14

WORKDIR /code

# Install system dependencies for Tesseract and Poppler
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-slv \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

ENV PYTHONPATH=/code/app:$PYTHONPATH

CMD ["fastapi", "run", "app/main.py", "--port", "8080"]