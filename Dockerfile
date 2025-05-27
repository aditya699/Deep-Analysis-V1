# Use the official Python 3.11 slim image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy all files from your local project into the container
COPY . .

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Start the FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
