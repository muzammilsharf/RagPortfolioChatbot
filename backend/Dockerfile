FROM python:3.11-slim

WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Start app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
