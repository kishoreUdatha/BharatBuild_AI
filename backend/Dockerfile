# ============================================
# BharatBuild AI Backend Dockerfile
# With Full AI/ML/Deep Learning Support
# ============================================

# Use Ubuntu base image (CUDA not needed for ECS deployment)
# For GPU support, switch to: nvidia/cuda:12.2.0-cudnn8-devel-ubuntu22.04
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    GOPATH=/go \
    PATH=$PATH:/usr/local/go/bin:/go/bin:/root/.local/bin \
    # CUDA environment
    CUDA_HOME=/usr/local/cuda \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Set working directory
WORKDIR /app

# ============================================
# Install System Dependencies
# ============================================
RUN apt-get update && apt-get install -y \
    # Python
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    # Build tools
    gcc \
    g++ \
    build-essential \
    cmake \
    ninja-build \
    # Database clients
    postgresql-client \
    libpq-dev \
    # System libraries
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    # Audio libraries (for speech AI)
    libsndfile1 \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    portaudio19-dev \
    # OpenCV dependencies
    libopencv-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    # HDF5 for Keras
    libhdf5-dev \
    # BLAS/LAPACK for scientific computing
    libopenblas-dev \
    liblapack-dev \
    # Git and utilities
    git \
    curl \
    wget \
    unzip \
    vim \
    htop \
    # Rust (for some Python packages)
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Install Java (for Spark, H2O, etc.)
# ============================================
RUN apt-get update && apt-get install -y \
    default-jdk \
    maven \
    gradle \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Install Node.js 20.x (for JS/TS projects)
# ============================================
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest typescript ts-node yarn pnpm && \
    rm -rf /var/lib/apt/lists/*

# ============================================
# Install Go 1.21 (for Go projects)
# ============================================
RUN wget -q https://go.dev/dl/go1.21.5.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz && \
    rm go1.21.5.linux-amd64.tar.gz && \
    mkdir -p /go/bin

# ============================================
# Install Ruby (for Ruby projects)
# ============================================
RUN apt-get update && apt-get install -y \
    ruby \
    ruby-dev \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Install PHP (for PHP projects)
# ============================================
RUN apt-get update && apt-get install -y \
    php \
    php-cli \
    php-mbstring \
    php-xml \
    composer \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Install Docker CLI (for sandbox containers)
# ============================================
RUN apt-get update && apt-get install -y \
    ca-certificates \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Set Python 3.11 as default
# ============================================
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    python -m pip install --upgrade pip setuptools wheel

# ============================================
# Install PyTorch with CUDA support first
# ============================================
RUN pip install torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0 \
    --index-url https://download.pytorch.org/whl/cu121

# ============================================
# Install TensorFlow with GPU support
# ============================================
RUN pip install tensorflow[and-cuda]==2.15.0

# ============================================
# Copy and install Python requirements
# ============================================
COPY requirements.txt .

# Install requirements (excluding torch/tensorflow which are already installed)
RUN pip install --no-cache-dir -r requirements.txt \
    --ignore-installed torch torchvision torchaudio tensorflow 2>&1 | tee /tmp/pip-install.log || \
    (cat /tmp/pip-install.log && exit 1)

# ============================================
# Download NLP models
# ============================================
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download en_core_web_md && \
    python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"

# ============================================
# Verify installations
# ============================================
RUN echo "=== Language & Framework Versions ===" && \
    python --version && \
    node --version && \
    npm --version && \
    java -version 2>&1 | head -1 && \
    /usr/local/go/bin/go version && \
    rustc --version && \
    ruby --version && \
    php --version | head -1 && \
    g++ --version | head -1 && \
    echo "=== AI/ML Framework Versions ===" && \
    python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')" && \
    python -c "import tensorflow as tf; print(f'TensorFlow: {tf.__version__}, GPU: {len(tf.config.list_physical_devices(\"GPU\"))}')" && \
    python -c "import sklearn; print(f'scikit-learn: {sklearn.__version__}')" && \
    python -c "import transformers; print(f'Transformers: {transformers.__version__}')" && \
    python -c "import langchain; print(f'LangChain: {langchain.__version__}')"

# ============================================
# Copy application code
# ============================================
COPY . .

# ============================================
# Create necessary directories
# ============================================
RUN mkdir -p uploads temp generated logs user_projects models datasets

# ============================================
# Expose ports
# ============================================
EXPOSE 8000
# JupyterLab port
EXPOSE 8888
# TensorBoard port
EXPOSE 6006
# MLflow port
EXPOSE 5000

# ============================================
# Run the application
# ============================================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
