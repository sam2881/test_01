FROM python:3.10-slim

WORKDIR /app

COPY ../../../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install GCP monitoring libraries
RUN pip install --no-cache-dir \
    google-cloud-monitoring==2.16.0 \
    google-cloud-compute==1.14.1 \
    google-cloud-logging==3.8.0

COPY ../../ /app/

ENV PYTHONPATH=/app

EXPOSE 8015

CMD ["python", "agents/gcp_monitor/agent.py"]
