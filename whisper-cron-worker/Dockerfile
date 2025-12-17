# Use NVIDIA CUDA base image with Node.js
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Install Node.js 20
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    ffmpeg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Whisper dependencies (Python)
RUN pip3 install --no-cache-dir openai-whisper torch torchaudio

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install Node.js dependencies
RUN npm ci --only=production

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x scripts/*.sh

# Create directories for media
RUN mkdir -p /media/input /media/output

# Expose API port
EXPOSE 3001

# Start the application
CMD ["node", "src/index.js"]

