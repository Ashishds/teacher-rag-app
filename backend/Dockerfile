FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy data directory (one level up)
COPY ../data ./data

# Expose port
EXPOSE 8000

# Run ingestion on first start, then start server
CMD python ingest.py && uvicorn main:app --host 0.0.0.0 --port 8000
