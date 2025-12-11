FROM python:3.11-slim

# System deps for python-magic and logging
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (better cache)
COPY requirements.txt .

# Install python packages
RUN pip install --no-cache-dir -r requirements.txt

# Ensure log and data directories exist
RUN mkdir -p /var/log/app /data /uploads_sandbox

# Copy application code
COPY . .

# Environment variables
ENV FLASK_ENV=production \
    PYTHONUNBUFFERED=1

# Expose Gunicorn port
EXPOSE 8000

# Run Gunicorn server
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
