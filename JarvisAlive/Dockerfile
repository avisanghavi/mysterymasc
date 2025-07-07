FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .
COPY . .

# Install Python dependencies
RUN pip install -e .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]