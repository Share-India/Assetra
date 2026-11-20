# AWS Lightsail Deployment Guide: Assetra (Multi-App Coexistence)

Complete step-by-step instructions to deploy **Assetra** on an **AWS Lightsail** instance that **already has other applications running on ports 80 and 443**.

---

## Architecture: Shared Lightsail Host

```
                            Incoming Traffic
                                   │
               ┌───────────────────┴───────────────────┐
               │                                       │
     Existing Domains                        assetra.shareindiainsurance.com
               │                                       │
               └───────────────────┬───────────────────┘
                                   │
                         Host Ports 80 & 443
                                   ▼
                ┌─────────────────────────────────────┐
                │        HOST NGINX WEB SERVER        │
                │  (Handles SSL & routes each domain) │
                └──────────────┬──────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
            ▼                                     ▼
   Existing Applications                proxy_pass http://127.0.0.1:8095
   (Completely untouched)                         │
                                                  ▼
                                      ┌───────────────────────┐
                                      │ Assetra Docker Web    │
                                      │ (Nginx + React SPA)   │
                                      └───────────┬───────────┘
                                                  │ http://backend:8000
                                                  ▼
                                      ┌───────────────────────┐
                                      │ Assetra Backend       │
                                      │ (FastAPI & WPI Engine)│
                                      └───────────┬───────────┘
                                                  │ MySQL :3306
                                                  ▼
                                      ┌───────────────────────┐
                                      │ Assetra MySQL DB      │
                                      │ (Volume: mysql_data)  │
                                      └───────────────────────┘
```

---

## Step 1: Pull the Updated Configuration on Lightsail

On your Lightsail terminal (`ubuntu@ip-172-26-8-130:~/Assetra$`):
```bash
git pull origin main
```
*This pulls the updated `docker-compose.yml` which assigns the frontend container to port **8080** instead of conflicting with port 80.*

---

## Step 2: Verify Port 8080 is Free

Run:
```bash
sudo ss -tulpn | grep 8095
```
If there is no output, port 8080 is free. *(If in use, you can set `ASSETRA_PORT=8085` in `.env`)*.

---

## Step 3: Start the Assetra Containers

```bash
docker compose up -d
```

Verify that all three containers are running:
```bash
docker compose ps
```
All containers will now show **Up / healthy**:
- `assetra-db` (healthy)
- `assetra-backend` (Up)
- `assetra-frontend` (Up, 0.0.0.0:8080->80/tcp)

---

## Step 4: Configure Host Nginx for `assetra.shareindiainsurance.com`

Create a new site configuration in your host's Nginx:

```bash
sudo nano /etc/nginx/sites-available/assetra.shareindiainsurance.com
```

Paste this configuration:

```nginx
server {
    listen 80;
    server_name assetra.shareindiainsurance.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8095;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Extended timeouts for large Excel valuations
        proxy_read_timeout 600s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 600s;
        proxy_buffering off;
    }
}
```
Save with `Ctrl + O`, `Enter`, and exit with `Ctrl + X`.

---

## Step 5: Enable Site and Reload Host Nginx

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/assetra.shareindiainsurance.com /etc/nginx/sites-enabled/

# Test syntax (ensures no disruption to other sites)
sudo nginx -t

# Reload Nginx (zero downtime for other running apps)
sudo systemctl reload nginx
```

---

## Step 6: Enable Free SSL with Certbot

Run Certbot on the host:
```bash
sudo certbot --nginx -d assetra.shareindiainsurance.com
```
Follow the prompt. Certbot will automatically configure HTTPS on port 443 for `assetra.shareindiainsurance.com` without touching any of your other existing domain certificates.

---

## Step 7: Create the Administrator Account

```bash
docker compose exec backend python seed_admin.py
```
Follow the prompt to set up your administrator email and password.

---

## Verification

Open your browser at:
**`https://assetra.shareindiainsurance.com`**
The application is live, SSL-secured, and operating completely independently alongside your other applications.
