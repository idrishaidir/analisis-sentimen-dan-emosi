FROM python:3.12-slim

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
CMD gunicorn --workers 1 --threads 1 -b 0.0.0.0:$PORT --timeout 300 app:app