FROM python:3.12-slim

# Install dependencies (ffmpeg + build tools + curl + unzip)
RUN apt-get update && \
    apt-get install -y ffmpeg gcc python3-dev curl unzip && \
    rm -rf /var/lib/apt/lists/*

# App setup
WORKDIR /app
COPY . .

# Upgrade pip (recommended)
RUN pip install --upgrade pip

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Install Deno
RUN curl -fsSL https://deno.land/install.sh | sh
ENV PATH="/root/.deno/bin:${PATH}"

CMD ["bash", "start"]
