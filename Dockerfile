# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm 

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install system dependencies that might be needed by packages in requirements.txt
# Add or remove packages here based on the actual errors you get from pip install
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install yt-dlp

# Copy the rest of the application code into the container at /app
COPY . /app

# Run bot.py when the container launches
CMD ["python3", "bot.py"]
