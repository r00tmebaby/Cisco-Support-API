# Use an official Python runtime as a parent image
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 8000

# Run uvicorn with multiple workers and threading
CMD ["uvicorn", "app/server:app", "--host", "0.0.0.0", "--port", "8000"]
