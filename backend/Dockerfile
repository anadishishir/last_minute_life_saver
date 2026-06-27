FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app source code
COPY app/ ./app/

# Environment variable PORT is dynamically set by Google Cloud Run
ENV PORT=8000
EXPOSE 8000

# Start FastAPI via uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
