FROM python:3.12-slim

# Install system dependencies & Playwright dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxcb1 libxkbcommon0 libatspi2.0-0 libx11-6 \
    libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js v20 for tweet-harvest (fixes EBADENGINE)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g tweet-harvest@latest \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV FLASK_ENV=production \
    ENVIRONMENT=production

# Run Gunicorn binding to the PORT environment variable provided by Render
CMD gunicorn --workers 1 --threads 1 -b 0.0.0.0:$PORT --timeout 120 app:app