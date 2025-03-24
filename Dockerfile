FROM python:3.9-slim

WORKDIR /app

# Install system dependency (ffmpeg is no longer used for merging, but still useful for potential diagnostics)
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port 8000 (if you plan to use a webhook or monitoring endpoint)
EXPOSE 8000

# Start the bot
CMD ["python", "main.py"]
