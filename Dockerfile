FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
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