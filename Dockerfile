
FROM python:3.11-slim
# Set working directory
WORKDIR /app

# Copy the requirements.txt file first for better caching 
COPY requirements.txt . 

# Install the necessary packages 
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port that the FastAPI app runs on 
EXPOSE 8085 

# Command to run the FastAPI application with uvicorn # CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] CMD ["python3", "main.py"]

# Run FastAPI app
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
