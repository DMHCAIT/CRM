# 🚀 Phase 3 Setup & Deployment Guide

**Background Task Processing with Celery + Redis**

---

## 📋 Prerequisites

### 1. Install Redis
Redis is required as the message broker and result backend.

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**Windows:**
```bash
# Download from https://redis.io/download
# Or use WSL/Docker
docker run -d -p 6379:6379 redis:latest
```

**Verify Redis:**
```bash
redis-cli ping
# Should return: PONG
```

---

### 2. Install Python Dependencies
```bash
cd /Users/guneswaribokam/crm/lead-ai/crm/backend

# Add to requirements.txt (if not already present):
echo "celery==5.3.4" >> requirements.txt
echo "redis==5.0.1" >> requirements.txt

# Install
pip install -r requirements.txt
```

---

## 🏃 Running Background Workers

### Development Mode (Local)

**Terminal 1 - Start Redis:**
```bash
redis-server
```

**Terminal 2 - Start Celery Worker:**
```bash
cd /Users/guneswaribokam/crm/lead-ai/crm/backend

# Start worker with all queues
celery -A celery_config worker -l info -Q bulk,ai,scheduled,messages

# Or start multiple workers for specific queues
celery -A celery_config worker -l info -Q bulk,ai -n worker1@%h
celery -A celery_config worker -l info -Q scheduled,messages -n worker2@%h
```

**Terminal 3 - Start Celery Beat (Scheduler):**
```bash
cd /Users/guneswaribokam/crm/lead-ai/crm/backend

celery -A celery_config beat -l info
```

**Terminal 4 - (Optional) Start Flower Monitoring:**
```bash
celery -A celery_config flower --port=5555

# Access at http://localhost:5555
```

**Terminal 5 - Start FastAPI Backend:**
```bash
cd /Users/guneswaribokam/crm/lead-ai/crm/backend
uvicorn main:app --reload
```

---

## 🔧 Configuration

### Environment Variables
Create `.env` file in `/backend/` directory:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@yourcompany.com

# WhatsApp Configuration (Meta Cloud API)
WHATSAPP_API_URL=https://graph.facebook.com/v18.0/{phone-number-id}/messages
WHATSAPP_API_KEY=your-meta-api-key

# Or Twilio
WHATSAPP_API_URL=https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json
WHATSAPP_API_KEY=your-twilio-auth-token
```

### Redis Configuration Options
```python
# celery_config.py
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# For production with authentication:
REDIS_URL = 'redis://:password@host:6379/0'

# For Redis Sentinel (high availability):
REDIS_URL = 'sentinel://sentinel1:26379;sentinel2:26379/mymaster/0'

# For Redis Cluster:
REDIS_URL = 'rediss://cluster1:6379,cluster2:6379,cluster3:6379/0'
```

---

## 🐳 Docker Deployment

### docker-compose.yml
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  celery-worker:
    build: ./backend
    command: celery -A celery_config worker -l info -Q bulk,ai,scheduled,messages
    depends_on:
      - redis
      - db
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=${DATABASE_URL}
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
    volumes:
      - ./backend:/app
      - ./models:/app/models
    restart: unless-stopped

  celery-beat:
    build: ./backend
    command: celery -A celery_config beat -l info
    depends_on:
      - redis
      - db
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - ./backend:/app
    restart: unless-stopped

  flower:
    build: ./backend
    command: celery -A celery_config flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery-worker
    environment:
      - REDIS_URL=redis://redis:6379/0
    restart: unless-stopped

volumes:
  redis_data:
```

### Start Docker Stack
```bash
docker-compose up -d redis celery-worker celery-beat flower
```

---

## 📊 Monitoring

### 1. Flower Dashboard
**URL:** http://localhost:5555

**Features:**
- Real-time task monitoring
- Worker status and stats
- Task history and results
- Rate limit management
- Task revocation (cancel)

### 2. Redis CLI Monitoring
```bash
# Monitor all commands
redis-cli MONITOR

# Check queue sizes
redis-cli LLEN bulk
redis-cli LLEN ai
redis-cli LLEN scheduled
redis-cli LLEN messages

# Check active tasks
redis-cli KEYS "celery-task-meta-*"
```

### 3. Performance Monitoring Dashboard
**URL:** http://localhost:3000/performance (in CRM UI)

---

## 🧪 Testing Background Jobs

### Test Individual Tasks
```bash
# Test email task
celery -A celery_config call message_queue.send_email_task \
  --args='["test@example.com", "Test Subject", "Test email body"]'

# Test WhatsApp task
celery -A celery_config call message_queue.send_whatsapp_task \
  --args='["+1234567890", "Test WhatsApp message"]'

# Test lead scoring
celery -A celery_config call background_tasks.ai_score_lead \
  --args='["L001"]'

# Test bulk update
celery -A celery_config call background_tasks.bulk_update_leads \
  --args='[["L001", "L002"], {"status": "contacted"}, 1]'
```

### Test Scheduled Jobs (Manual Trigger)
```bash
# Send daily performance report
celery -A celery_config call scheduled_jobs.send_daily_performance_report

# Auto-assign unassigned leads
celery -A celery_config call scheduled_jobs.auto_assign_unassigned_leads

# Trigger stale lead workflow
celery -A celery_config call scheduled_jobs.trigger_stale_lead_workflow
```

### Test via API
```bash
# Queue bulk email
curl -X POST http://localhost:8000/api/tasks/bulk-email \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": ["test1@example.com", "test2@example.com"],
    "subject": "Test Bulk Email",
    "body": "This is a test message"
  }'

# Check task status
curl http://localhost:8000/api/tasks/{task_id}/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get active tasks
curl http://localhost:8000/api/tasks/active \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔥 Production Deployment

### 1. Systemd Service (Linux)

**celery-worker.service:**
```ini
[Unit]
Description=Celery Worker Service
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/crm/backend
Environment="PATH=/var/www/crm/venv/bin"
ExecStart=/var/www/crm/venv/bin/celery -A celery_config worker \
  -l info -Q bulk,ai,scheduled,messages \
  --pidfile=/var/run/celery/worker.pid \
  --logfile=/var/log/celery/worker.log
ExecStop=/var/www/crm/venv/bin/celery -A celery_config control shutdown
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**celery-beat.service:**
```ini
[Unit]
Description=Celery Beat Service
After=network.target redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/crm/backend
Environment="PATH=/var/www/crm/venv/bin"
ExecStart=/var/www/crm/venv/bin/celery -A celery_config beat \
  -l info \
  --pidfile=/var/run/celery/beat.pid \
  --logfile=/var/log/celery/beat.log
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Install and Start:**
```bash
# Copy service files
sudo cp celery-worker.service /etc/systemd/system/
sudo cp celery-beat.service /etc/systemd/system/

# Create log directories
sudo mkdir -p /var/run/celery /var/log/celery
sudo chown www-data:www-data /var/run/celery /var/log/celery

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat

# Check status
sudo systemctl status celery-worker
sudo systemctl status celery-beat

# View logs
sudo journalctl -u celery-worker -f
sudo journalctl -u celery-beat -f
```

---

### 2. Supervisor (Alternative)

**supervisord.conf:**
```ini
[program:celery-worker]
command=/var/www/crm/venv/bin/celery -A celery_config worker -l info -Q bulk,ai,scheduled,messages
directory=/var/www/crm/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/celery/worker.err.log
stdout_logfile=/var/log/celery/worker.out.log

[program:celery-beat]
command=/var/www/crm/venv/bin/celery -A celery_config beat -l info
directory=/var/www/crm/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/celery/beat.err.log
stdout_logfile=/var/log/celery/beat.out.log
```

**Start:**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery-worker celery-beat
sudo supervisorctl status
```

---

## 🛡️ Security Best Practices

### 1. Redis Security
```bash
# Edit /etc/redis/redis.conf

# Require password
requirepass your_strong_password_here

# Bind to localhost only
bind 127.0.0.1

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

### 2. Environment Variables
```bash
# Never commit .env file
echo ".env" >> .gitignore

# Use secrets management in production
# - AWS Secrets Manager
# - Google Cloud Secret Manager
# - HashiCorp Vault
```

### 3. Rate Limiting
Already configured in `message_queue.py`:
```python
@celery_app.task(rate_limit='100/m')  # Max 100 emails/min
def send_bulk_email(...):
    ...

@celery_app.task(rate_limit='50/m')  # Max 50 WhatsApp/min
def send_bulk_whatsapp(...):
    ...
```

---

## 📈 Scaling Workers

### Horizontal Scaling (Multiple Machines)
```bash
# Machine 1 - Bulk tasks
celery -A celery_config worker -l info -Q bulk -n bulk-worker@machine1

# Machine 2 - AI tasks
celery -A celery_config worker -l info -Q ai -n ai-worker@machine2

# Machine 3 - Messages
celery -A celery_config worker -l info -Q messages -n msg-worker@machine3
```

### Vertical Scaling (Concurrency)
```bash
# Increase concurrency (default: CPU cores)
celery -A celery_config worker -l info --concurrency=16

# Use eventlet for I/O bound tasks
celery -A celery_config worker -l info -P eventlet --concurrency=100

# Use gevent
celery -A celery_config worker -l info -P gevent --concurrency=100
```

---

## 🔍 Troubleshooting

### Worker Not Connecting to Redis
```bash
# Check Redis is running
redis-cli ping

# Check Redis URL
echo $REDIS_URL

# Test connection
python -c "import redis; r = redis.from_url('redis://localhost:6379/0'); print(r.ping())"
```

### Tasks Not Executing
```bash
# Check worker is running
celery -A celery_config inspect active

# Check queue routing
celery -A celery_config inspect active_queues

# Purge queue
celery -A celery_config purge
```

### Email/WhatsApp Not Sending
```bash
# Check environment variables
echo $SMTP_USER
echo $WHATSAPP_API_URL

# Test SMTP connection
python -c "import smtplib; s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); print('OK')"

# View task logs
celery -A celery_config events
```

### High Memory Usage
```bash
# Reduce concurrency
celery -A celery_config worker -l info --concurrency=4

# Use max tasks per child
celery -A celery_config worker -l info --max-tasks-per-child=100

# Monitor memory
celery -A celery_config inspect stats
```

---

## ✅ Deployment Checklist

- [ ] Redis installed and running
- [ ] Redis password configured
- [ ] Python dependencies installed
- [ ] Environment variables set
- [ ] Email SMTP credentials configured
- [ ] WhatsApp API credentials configured
- [ ] Celery worker service configured
- [ ] Celery beat service configured
- [ ] Flower monitoring (optional) configured
- [ ] Logs directory created
- [ ] Systemd/Supervisor services enabled
- [ ] Firewall rules configured (6379 for Redis)
- [ ] Monitoring alerts set up
- [ ] Backup strategy for Redis data

---

## 📞 Support

If you encounter issues:

1. **Check logs:**
   ```bash
   sudo journalctl -u celery-worker -f
   sudo journalctl -u celery-beat -f
   ```

2. **Check Flower dashboard:** http://localhost:5555

3. **Check Redis:**
   ```bash
   redis-cli INFO
   redis-cli MONITOR
   ```

4. **View task history:**
   ```bash
   celery -A celery_config inspect registered
   celery -A celery_config inspect scheduled
   ```

---

**Setup Complete! 🎉**

Your CRM now has enterprise-grade background task processing with:
- ✅ Async bulk operations
- ✅ Scheduled automation jobs
- ✅ Reliable message delivery
- ✅ Real-time monitoring

Next: Test the system and proceed to **Phase 4: Advanced Analytics**.
