# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm 

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install system dependencies, including ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --upgrade yt-dlp

# Copy cookies.txt specifically and set environment variable
COPY cookies.txt /app/cookies.txt

# Copy the rest of the application code into the container at /app
COPY . /app

# Run bot.py when the container launches
CMD ["python3", "bot.py"]
