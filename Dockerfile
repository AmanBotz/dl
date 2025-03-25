# Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY . .

# Expose port 8000 for health checks
EXPOSE 8000

# Run the main application
CMD ["python", "main.py"]
