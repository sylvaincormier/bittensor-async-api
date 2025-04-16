FROM python:3.10-slim
WORKDIR /app

# System deps - include all requirements for bittensor
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    pkg-config \
    curl \
    git \
    cmake \
    protobuf-compiler \
    python3-dev \
    libgmp-dev \
    && rm -rf /var/lib/apt/lists/*

# Install latest Rust compiler (required for bittensor)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python deps with detailed logs
RUN pip install --upgrade pip && \
    pip install setuptools_rust && \
    pip install --verbose bittensor==9.3.0 && \
    pip install --no-cache-dir -r requirements.txt

# Add code last to optimize rebuilds
COPY . .
CMD ["uvicorn", "bittensor_async_app.main:app", "--host", "0.0.0.0", "--port", "8000"]