FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY ../../../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY ../../ /app/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8010

# Run agent
CMD ["python", "agents/servicenow/agent.py"]
