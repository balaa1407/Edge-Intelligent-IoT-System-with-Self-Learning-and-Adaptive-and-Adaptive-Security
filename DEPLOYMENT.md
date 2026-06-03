# Deployment Guide

Instructions for deploying the Edge IoT system to different environments.

## Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run in development
python bridge.py &
python app.py

# Access dashboard
open http://localhost:5000
```

## Docker Deployment

### Single Container

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')"

# Start both services
CMD sh -c 'python bridge.py & python app.py'
```

Build and run:
```bash
docker build -t edge-iot .
docker run -p 5000:5000 \
  -e MQTT_BROKER=mosquitto \
  -e TEMP_MIN=18.0 \
  -e TEMP_MAX=28.0 \
  edge-iot
```

### Docker Compose

```yaml
version: '3.8'

services:
  mosquitto:
    image: eclipse-mosquitto:latest
    ports:
      - "1883:1883"
    volumes:
      - mosquitto_data:/mosquitto/data
    networks:
      - edge-iot

  bridge:
    build: .
    depends_on:
      - mosquitto
    environment:
      MQTT_BROKER: mosquitto
      MQTT_PORT: 1883
      LOG_LEVEL: INFO
    networks:
      - edge-iot
    command: python bridge.py

  app:
    build: .
    depends_on:
      - bridge
    ports:
      - "5000:5000"
    environment:
      FLASK_ENV: production
    networks:
      - edge-iot
    command: python app.py

volumes:
  mosquitto_data:

networks:
  edge-iot:
```

Start:
```bash
docker-compose up -d
```

## Kubernetes Deployment

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: edge-iot
```

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: edge-iot-config
  namespace: edge-iot
data:
  MQTT_BROKER: "mosquitto.edge-iot.svc.cluster.local"
  MQTT_PORT: "1883"
  TEMP_MIN: "18.0"
  TEMP_MAX: "28.0"
  ANOMALY_THRESHOLD: "2.5"
  LOG_LEVEL: "INFO"
```

### Bridge Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edge-iot-bridge
  namespace: edge-iot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: edge-iot-bridge
  template:
    metadata:
      labels:
        app: edge-iot-bridge
    spec:
      containers:
      - name: bridge
        image: edge-iot:latest
        command: ["python", "bridge.py"]
        envFrom:
        - configMapRef:
            name: edge-iot-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import os; os.path.exists('/tmp/bridge.pid')"
          initialDelaySeconds: 30
          periodSeconds: 10
```

### Flask App Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edge-iot-app
  namespace: edge-iot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: edge-iot-app
  template:
    metadata:
      labels:
        app: edge-iot-app
    spec:
      containers:
      - name: app
        image: edge-iot:latest
        command: ["python", "app.py"]
        ports:
        - containerPort: 5000
        envFrom:
        - configMapRef:
            name: edge-iot-config
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: edge-iot-service
  namespace: edge-iot
spec:
  selector:
    app: edge-iot-app
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 5000
```

Deploy to K8s:
```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f bridge-deployment.yaml
kubectl apply -f app-deployment.yaml
kubectl apply -f service.yaml
```

## Cloud Deployment (AWS)

### EC2 Instance

1. Launch Ubuntu 22.04 instance
2. Security group: Allow 5000 (Flask)
3. Elastic IP for consistency

Setup:
```bash
#!/bin/bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip git

git clone <repo>
cd edge-iot-system
pip install -r requirements.txt

# Run with systemd
sudo cp systemd/edge-iot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable edge-iot
sudo systemctl start edge-iot
```

### RDS/S3 Integration

For persistence:
```python
import boto3

# Store data in S3
s3 = boto3.client('s3')

def backup_log():
    """Backup log.json to S3."""
    s3.upload_file('log.json', 'edge-iot-backups', f'log-{timestamp}.json')

# Call periodically
```

## Production Checklist

```
DEPLOYMENT
- [ ] Database setup (if using)
- [ ] TLS certificates installed
- [ ] Environment variables configured
- [ ] Firewall rules configured
- [ ] Backup strategy in place
- [ ] Monitoring configured

SECURITY
- [ ] MQTT credentials changed from defaults
- [ ] Flask debug mode disabled
- [ ] CORS configured appropriately
- [ ] Input validation enabled
- [ ] Rate limiting enabled
- [ ] Secrets in environment variables

PERFORMANCE
- [ ] Caching enabled
- [ ] Compression enabled
- [ ] Log rotation configured
- [ ] Resource limits set
- [ ] Scaling strategy planned

MONITORING
- [ ] Health checks configured
- [ ] Logging enabled
- [ ] Alerts configured
- [ ] Metrics collection enabled
- [ ] Uptime monitoring enabled
```

## Systemd Service

```ini
# /etc/systemd/system/edge-iot-bridge.service
[Unit]
Description=Edge IoT MQTT Bridge
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/edge-iot
Environment="PATH=/home/pi/edge-iot/venv/bin"
ExecStart=/home/pi/edge-iot/venv/bin/python bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable edge-iot-bridge
sudo systemctl start edge-iot-bridge
sudo systemctl status edge-iot-bridge
```

## Monitoring Integration

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, start_http_server

# Metrics
messages_processed = Counter('edge_iot_messages_processed', 'Messages processed')
processing_time = Histogram('edge_iot_processing_seconds', 'Processing time')

# Export metrics
start_http_server(8000)

# Use in code
messages_processed.inc()
with processing_time.time():
    process_message()
```

### Health Check

```bash
curl http://localhost:5000/health
# {"status": "ok", "timestamp": "...", "service": "..."}

# For monitoring
curl -f http://localhost:5000/health || exit 1
```

## Backup Strategy

```bash
#!/bin/bash
# Daily backup script

BACKUP_DIR=/backups/edge-iot
DATE=$(date +%Y%m%d_%H%M%S)

# Backup log file
cp log.json $BACKUP_DIR/log_$DATE.json

# Compress old backups
gzip $BACKUP_DIR/log_*.json

# Keep only 30 days
find $BACKUP_DIR -mtime +30 -delete

# Upload to cloud (optional)
aws s3 cp $BACKUP_DIR/log_$DATE.json.gz s3://backups/edge-iot/
```

Cron job:
```bash
0 2 * * * /home/pi/edge-iot/backup.sh
```

## Rollback Procedure

If deployment fails:

```bash
# 1. Stop services
systemctl stop edge-iot-bridge
systemctl stop edge-iot-app

# 2. Restore from backup
cp /backups/edge-iot/log_backup.json log.json

# 3. Restore code version
git checkout <previous-tag>

# 4. Restart services
systemctl start edge-iot-bridge
systemctl start edge-iot-app

# 5. Verify
curl http://localhost:5000/health
```

## Upgrade Procedure

```bash
# 1. Test in staging first
# 2. Backup current data
cp log.json log.json.backup

# 3. Stop services
systemctl stop edge-iot-app edge-iot-bridge

# 4. Update code
git pull origin main
pip install -r requirements.txt

# 5. Run migrations (if any)
python migrations.py

# 6. Restart services
systemctl start edge-iot-bridge
systemctl start edge-iot-app

# 7. Verify
curl http://localhost:5000/health

# 8. Monitor logs
tail -f /var/log/edge-iot.log
```
