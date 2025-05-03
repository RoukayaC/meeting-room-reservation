FROM python:3.11-slim AS builder

WORKDIR /app
# Copy only the requirements file for this specific service first
COPY services/reservation-service/requirements.txt .
# Install dependencies into a temporary location
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim
WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /install /usr/local

# Copy the application code for this specific service
COPY services/reservation-service/ ./

# Copy the shared utilities from the correct path relative to the build context
COPY services/shared/ ./shared


# Expose the port the app runs on
EXPOSE 5000

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
