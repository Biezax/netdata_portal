# Nginx Configuration Example

## Quick Setup

1. **Install Nginx:**
   ```bash
   sudo apt install nginx
   ```

2. **Copy configuration:**
   ```bash
   sudo cp examples/nginx.conf /etc/nginx/sites-available/netdata-aggregator
   ```

3. **Edit configuration:**
   ```bash
   sudo nano /etc/nginx/sites-available/netdata-aggregator
   ```

   Replace:
   - `netdata.example.com` → your domain
   - SSL certificate paths (if using Let's Encrypt)

4. **Enable site:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/netdata-aggregator /etc/nginx/sites-enabled/
   ```

5. **Test configuration:**
   ```bash
   sudo nginx -t
   ```

6. **Reload Nginx:**
   ```bash
   sudo systemctl reload nginx
   ```

## SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d netdata.example.com

# Auto-renewal is configured automatically
```

## Without SSL (HTTP only)

If you don't need HTTPS, use this minimal config:

```nginx
server {
    listen 80;
    server_name netdata.example.com;

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Basic Authentication (Optional)

Add password protection:

```bash
# Install apache2-utils
sudo apt install apache2-utils

# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Uncomment auth_basic section in nginx.conf
```

## Firewall

Allow HTTP/HTTPS:

```bash
sudo ufw allow 'Nginx Full'
```

## Troubleshooting

**Check logs:**
```bash
sudo tail -f /var/log/nginx/netdata-aggregator-error.log
```

**Test backend:**
```bash
curl http://localhost:8000/health
```

**Test frontend:**
```bash
curl http://localhost:3000
```
