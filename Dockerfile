# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Ensure config.txt is present (as per user's request, though it's covered by COPY . .)
# If config.txt was not in the root, we would need a specific COPY instruction for it.

# Run bot.py when the container launches
CMD ["python3", "bot.py"]
