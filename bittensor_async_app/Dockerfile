# Use an official Python image as base
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directory and set permissions
WORKDIR /app
RUN chown appuser:appuser /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libssl-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Rust using a secure approach (download first, verify, then execute)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o rustup-init.sh && \
    chmod +x rustup-init.sh && \
    ./rustup-init.sh -y && \
    rm rustup-init.sh

# Set PATH to include cargo binaries
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy requirements file separately to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Mark Docker container as running in Docker
ENV IS_DOCKER=true

# Expose port for the FastAPI application
EXPOSE 8000

# Set entrypoint command
CMD ["uvicorn", "bittensor_async_app.main:app", "--host", "0.0.0.0", "--port", "8000"]