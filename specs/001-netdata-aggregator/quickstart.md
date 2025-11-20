# Quickstart Guide: Netdata Aggregator

**Goal**: Get the Netdata Multi-Instance Aggregator running in under 5 minutes.

## Prerequisites

- Docker & Docker Compose installed
- At least 1 running Netdata instance accessible from your machine
- Netdata instances running on default port 19999

## Step 1: Clone & Configure (1 minute)

```bash
# Clone repository
git clone <repo-url>
cd netdata_portal

# Create configuration files
cp .env.example .env

# Create hosts file
cat > config/hosts.txt <<EOF
http://host1:19999
http://host2:19999
http://host3:19999
EOF
```

**Replace** `host1`, `host2`, `host3` with your actual Netdata hostnames/IPs.

**Example for local testing**:
```bash
# config/hosts.txt
http://192.168.1.100:19999
http://192.168.1.101:19999
```

## Step 2: Start Services (2 minutes)

```bash
# Build and start (first run takes ~2min for image build)
docker compose up -d

# Verify services running
docker compose ps

# Check logs
docker compose logs -f
```

Expected output:
```
netdata-aggregator-backend  | INFO: Uvicorn running on http://0.0.0.0:8000
netdata-aggregator-frontend | ▲ Next.js ready on http://0.0.0.0:3000
```

## Step 3: Access Dashboard (30 seconds)

Open browser: **http://localhost:3000**

**You should see**:
1. Left sidebar with your configured hosts
2. Top navigation with "Dashboard" and "Alerts" buttons
3. Click a host → See its Netdata dashboard in main area
4. Click "Alerts" → See aggregated alerts from all hosts

## Validation Checklist

- [ ] Sidebar shows all configured hosts
- [ ] Clicking a host loads its dashboard
- [ ] Dashboard is fully interactive (charts, zooming work)
- [ ] "Alerts" view shows combined alerts (if any active)
- [ ] Unreachable hosts show error message in Netdata style
- [ ] No console errors in browser DevTools

## Troubleshooting

### "Connection timeout" for all hosts

**Cause**: Hosts not reachable from backend container

**Fix**:
```bash
# Edit config/hosts.txt
# If using localhost/127.0.0.1, use host.docker.internal instead
http://host.docker.internal:19999

# Or use actual network IP
http://192.168.1.100:19999

# Changes auto-reload in ~5 seconds (no restart needed)
```

### Dashboard iframe shows "Refused to connect"

**Cause**: CORS or CSP issue

**Fix**: Verify proxy is working:
```bash
curl http://localhost:8000/api/proxy/host1/v3/
# Should return HTML (Netdata dashboard page)
```

If curl works but browser doesn't, check browser console for CSP errors.

### "Hostname not in configured hosts" error

**Cause**: Hostname mismatch between config and URL

**Fix**: Ensure exact match:
```bash
# Config has "prod-db-01" but you're accessing "prod-db-01.local"
# Update config/hosts.txt to match:
http://prod-db-01.local:19999
```

### No alerts showing (but hosts are reachable)

**Cause**: Netdata instances have no active alarms

**Verify**:
```bash
curl http://host1:19999/api/v1/alarms
# Should return JSON with active alarms
```

If response is empty (`"alarms": {}`), no alerts are active (expected behavior).

## Configuration Changes

### Add a new host (automatic reload)

```bash
# Edit config/hosts.txt
nano config/hosts.txt

# Add new host on a new line
http://host1:19999
http://host2:19999
http://new-host:19999

# Save file
# Backend detects change within ~5 seconds
# Refresh browser to see new host in sidebar
```

**No restart needed** (auto-reload via file polling).

### Adjust polling interval

```bash
# Edit .env
ALERT_POLL_INTERVAL=30  # Change from 15s to 30s

# Restart backend
docker compose restart backend
```

## Production Deployment

### Configuration

**Required**:
- `config/hosts.txt` - List of Netdata URLs (one per line)

**Environment Variables** (optional, defaults shown):
- `ALERT_POLL_INTERVAL=15` - Seconds between alert polls
- `REQUEST_TIMEOUT=5` - Timeout for Netdata requests
- `PORT=8000` - Backend API port
- `FRONTEND_PORT=3000` - Frontend port (dev only, production serves via backend)

### Docker Compose Override (Production)

Create `docker-compose.prod.yml`:
```yaml
services:
  backend:
    environment:
      - ENVIRONMENT=production
    ports:
      - "80:8000"  # Expose on port 80
    restart: always

  frontend:
    build:
      args:
        - NODE_ENV=production
```

Run:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

See `k8s/deployment.yaml` (if provided) or:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: netdata-hosts
data:
  hosts.txt: |
    http://netdata-1:19999
    http://netdata-2:19999

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netdata-aggregator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: netdata-aggregator
  template:
    metadata:
      labels:
        app: netdata-aggregator
    spec:
      containers:
      - name: backend
        image: netdata-aggregator:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: hosts-config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: hosts-config
        configMap:
          name: netdata-hosts
```

## Performance Benchmarks

Expected performance (20 configured hosts):

- **Dashboard load**: <500ms (SC-007)
- **Alert view load**: <20s (SC-002, includes 15s poll cycle)
- **Config reload**: ~5s (file polling)
- **Memory usage**: ~150MB backend, ~50MB frontend
- **CPU usage**: <5% idle, <20% during polling spikes

## Next Steps

1. **Customize theme**: Edit `frontend/styles/netdata-theme.css` to match your Netdata colors
2. **Add monitoring**: Integrate backend `/health` endpoint with your monitoring system
3. **Enable HTTPS**: Add reverse proxy (nginx/Caddy) with SSL certs
4. **Scale hosts**: Test with 50+ hosts (should remain responsive per SC-003)

## Support

- **Logs**: `docker compose logs -f`
- **Health check**: `curl http://localhost:8000/health`
- **API docs**: http://localhost:8000/docs (FastAPI auto-generated)
