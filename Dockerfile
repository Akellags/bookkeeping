FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (for PDF processing)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libmagic1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONPATH=/app
ENV PORT=8080

# Expose the port FastAPI runs on
EXPOSE 8080

# Use shell form with exec for correct signal handling and env var expansion
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"]
