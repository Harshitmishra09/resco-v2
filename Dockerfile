# ---- Base image ----
FROM python:3.11-slim

# ---- System dependencies ----
# Install Chromium, ChromeDriver, Tesseract OCR, and other required libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    libxrandr2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Environment variables for Chrome and Tesseract ----
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- Working directory ----
WORKDIR /app

# ---- Install Python dependencies ----
COPY requirements_prod.txt .
RUN pip install --no-cache-dir -r requirements_prod.txt

# ---- Copy application code ----
COPY . .

# ---- Create directories for output ----
RUN mkdir -p results

# ---- Expose port (Cloud Run injects $PORT, default 8080) ----
EXPOSE 8080

# ---- Run with Gunicorn ----
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 120 app:app
