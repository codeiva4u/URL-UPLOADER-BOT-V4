FROM python:3.10-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg jq python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy cookies file separately to ensure it's properly included
COPY cookies.txt /app/cookies.txt

# Copy the rest of the application
COPY . .

# Verify yt-dlp installation and cookies file
RUN python3 -m pip check yt-dlp && \
    ls -la /app/cookies.txt && \
    chmod 644 /app/cookies.txt

CMD ["python3", "bot.py"]