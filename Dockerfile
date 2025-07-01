# Use a slim Python 3.9 image as the base
FROM python:3.9-slim-buster

# Set the working directory inside the container
# All subsequent commands will run from here unless specified otherwise
WORKDIR /app

# Upgrade pip to the latest version
RUN pip install --no-cache-dir --upgrade pip

# Copy only the requirements file first to leverage Docker's build cache
COPY requirements.txt .
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the rest of the application code and directories into the working directory
# This includes main.py, templates/, static/, and feedback.db (if it exists locally)
COPY . .

# Command to run the application using Uvicorn
# 'main:app' means run the 'app' object from the 'main.py' file
# --host 0.0.0.0 makes it accessible from outside the container
# --port 5000 is the port the application listens on
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]