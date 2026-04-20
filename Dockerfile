# Use an explicitly versioned, lightweight Python image
FROM python:3.11-slim

# Create a specific unprivileged user and group for maximum security
# UID 10001 is typically safe and doesn't collide with host UIDs
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Set environment variables for optimized Python execution
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Set the working directory
WORKDIR /app

# Copy dependency file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies safely
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership of the application directory to the unprivileged user
RUN chown -R appuser:appgroup /app

# Switch to the unprivileged user
USER 10001

# Expose the Cloud Run port
EXPOSE 8080

# Run the application using Gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
