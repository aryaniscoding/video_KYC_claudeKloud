FROM python:3.11-slim

WORKDIR /app

# System deps: OpenCV (libGL), audio (libsndfile1/ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so this layer is cached on code-only changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full application (includes models/, config/, alembic/, migrations/)
COPY . .

EXPOSE 8000

# Run DB migrations then start with 1 worker (scale up on paid Render plans)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
