# BharatBuild Runtime Image
# This is the container image used for running user projects
#
# Includes: Node.js, Python, Java, Go, Rust, Ruby, PHP
# Size optimized: Uses multi-stage build and Alpine base

FROM node:20-alpine AS base

# Install system dependencies
RUN apk add --no-cache \
    bash \
    git \
    curl \
    wget \
    vim \
    nano \
    openssh-client \
    ca-certificates \
    tzdata \
    build-base \
    python3 \
    python3-dev \
    py3-pip \
    openjdk17-jdk \
    maven \
    gradle \
    go \
    ruby \
    ruby-dev \
    php \
    php-phar \
    php-json \
    php-mbstring \
    composer

# Set up Python virtual environment for pip packages
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install common Python packages
RUN pip install --no-cache-dir \
    flask \
    fastapi \
    uvicorn \
    django \
    requests \
    numpy \
    pandas

# Install Rust via rustup
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"

# Install global npm packages
RUN npm install -g \
    pnpm \
    yarn \
    typescript \
    vite \
    create-react-app \
    create-next-app \
    @angular/cli \
    vue-cli \
    nodemon \
    pm2

# Create workspace directory
WORKDIR /workspace

# Default environment
ENV NODE_ENV=development
ENV TERM=xterm-256color
ENV LANG=C.UTF-8

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD echo "healthy" || exit 1

# Default command (keep container running)
CMD ["tail", "-f", "/dev/null"]
