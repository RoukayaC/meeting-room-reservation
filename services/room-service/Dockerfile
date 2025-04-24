FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy shared utilities
COPY ../shared /app/shared

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app \
    FLASK_ENV=production \
    PYTHONPATH="${PYTHONPATH}:/app:/app/shared"

# Expose port
EXPOSE 5000

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]