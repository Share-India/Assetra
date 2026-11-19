# AWS Lightsail Deployment Guide: Assetra

Complete step-by-step instructions to deploy **Assetra (Fixed Asset Replacement Value Calculator)** on **AWS Lightsail** using **Docker**, **Nginx**, and **Let's Encrypt SSL** on the domain **`assetra.shareindiainsurance.com`**.

---

## Architecture Overview

```
                                      Internet
                                          │
                    ┌─────────────────────▼─────────────────────┐
                    │ Domain: assetra.shareindiainsurance.com   │
                    │ DNS A Record -> Lightsail Static IP       │
                    └─────────────────────┬─────────────────────┘
                                          │ Ports 80 / 443
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    Nginx (Container: assetra-frontend)│
                      │  • Serves React SPA (Static assets)   │
                      │  • Let's Encrypt SSL termination      │
                      │  • Reverse proxies API to backend     │
                      └──────────────┬────────────────────────┘
                                     │ http://backend:8000
                                     ▼
                      ┌───────────────────────────────────────┐
                      │    FastAPI (Container: assetra-backend)│
                      │  • Python 3.12 Engine / WPI Series    │
                      │  • Excel processing & calculation     │
                      └──────────────┬────────────────────────┘
                                     │ MySQL port 3306
                                     ▼
                      ┌───────────────────────────────────────┐
                      │    MySQL 8.0 (Container: assetra-db)  │
                      │  • Persistent volume: mysql_data      │
                      │  • User accounts, audit logs, caches  │
                      └───────────────────────────────────────┘
```

---

## Step 1: Create and Configure AWS Lightsail Instance

1. Log in to the [AWS Lightsail Console](https://lightsail.aws.amazon.com/).
2. Click **Create instance**.
3. Select your preferred AWS Region (e.g., **Mumbai `ap-south-1`** for India).
4. Platform: **Linux/Unix**.
5. Blueprint: **OS Only** -> **Ubuntu 22.04 LTS** (or Ubuntu 24.04 LTS).
6. Instance Plan:
   - **Recommended:** Minimum **$10/month** or **$20/month** plan (**2 GB RAM or 4 GB RAM**, 1-2 vCPUs, 60-80 GB SSD).
   - *Note: Pandas processing on large Excel sheets with tens of thousands of rows performs best with at least 2 GB RAM.*
7. Name your instance (e.g., `assetra-production`).
8. Click **Create instance**.

---

## Step 2: Allocate & Attach a Static IP

By default, Lightsail changes IP on reboot unless a Static IP is attached.

1. In Lightsail console, go to the **Networking** tab.
2. Click **Create static IP**.
3. Attach it to your newly created instance (`assetra-production`).
4. Note down your public IP (e.g., `13.235.xx.xx`).

---

## Step 3: Configure DNS for your Domain

In your DNS provider (e.g., Cloudflare, Route53, GoDaddy):
- Add an **A Record**:
  - **Name / Host:** `assetra` (or `assetra.shareindiainsurance.com`)
  - **Type:** `A`
  - **Value / Points to:** `<Your Lightsail Static IP>`
  - **TTL:** Auto or 300 seconds

---

## Step 4: Configure Lightsail Firewall

In Lightsail console -> Select instance -> **Networking** tab -> **IPv4 Firewall**:
Ensure the following ports are open:
- **SSH (Port 22)** (TCP) - Restricted to your IP or standard
- **HTTP (Port 80)** (TCP) - Anywhere (0.0.0.0/0)
- **HTTPS (Port 443)** (TCP) - Anywhere (0.0.0.0/0)

---

## Step 5: Connect and Install Docker on the Server

Click **Connect using SSH** in the Lightsail browser console, or use your SSH client:
```bash
ssh -i your-key.pem ubuntu@<your-static-ip>
```

Run the following commands on the server to install Docker and Docker Compose:
```bash
# Update package lists
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y curl apt-transport-https ca-certificates software-properties-common certbot

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu

# Apply group changes
newgrp docker

# Verify Docker and Docker Compose
docker --version
docker compose version
```

---

## Step 6: Clone the Repository

```bash
cd /home/ubuntu
git clone https://github.com/Share-India/Assetra.git
cd Assetra
```

---

## Step 7: Configure Environment Variables (.env)

Create the production `.env` file in the root project directory:
```bash
cp .env.example .env
nano .env
```

Set the production variables:
```ini
# ==============================================================================
# Assetra Production Environment Variables
# ==============================================================================

# Database Passwords (use strong, unique passwords)
DB_ROOT_PASSWORD=AssetraRoot2026!ChangeMeNow
DB_NAME=far_app
DB_USER=far_user
DB_PASSWORD=AssetraUserPass2026!ChangeMeNow

# Gemini AI API Key (from Google AI Studio: https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash

# Application URLs & CORS
FRONTEND_URL=https://assetra.shareindiainsurance.com

# JWT Secret (Generate random 64-char string: openssl rand -hex 32)
JWT_SECRET=generate_and_paste_a_random_64_character_hex_string_here

# App Limits
MAX_UPLOAD_MB=100
MAX_ROWS_PER_FILE=50000
DAILY_ANALYSES_PER_USER=20

# Access Control
ALLOWED_EMAIL_DOMAINS=shareindia.com,shareindiainsurance.com
ADMIN_EMAIL=communication.ins@shareindia.co.in
REQUIRE_ADMIN_APPROVAL=false
REQUIRE_EMAIL_VERIFICATION=true

# SMTP Email Configuration (for OTP and notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=communication.ins@shareindia.co.in
SMTP_PASSWORD=your_email_app_password
MAIL_FROM=communication.ins@shareindia.co.in
MAIL_SENDER_NAME="Share India Insurance"

LOG_LEVEL=INFO
```

Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit `nano`.

---

## Step 8: Build and Start Containers (HTTP Mode First)

Make sure certbot challenge directory exists:
```bash
sudo mkdir -p /var/www/certbot
sudo mkdir -p /etc/letsencrypt
```

Start the application stack:
```bash
docker compose up -d --build
```

Verify that all containers are healthy:
```bash
docker compose ps
```
You should see:
- `assetra-db` (healthy)
- `assetra-backend` (running)
- `assetra-frontend` (running, ports 80 and 443)

Verify that the site is reachable over HTTP by opening:
`http://assetra.shareindiainsurance.com`

---

## Step 9: Obtain Free Let's Encrypt SSL Certificate

Run Certbot on the Lightsail host to issue the certificate for your domain:
```bash
sudo certbot certonly --webroot -w /var/www/certbot \
  -d assetra.shareindiainsurance.com \
  --email communication.ins@shareindia.co.in \
  --agree-tos \
  --no-eff-email
```

Certbot will save the certificate files to:
`/etc/letsencrypt/live/assetra.shareindiainsurance.com/`

---

## Step 10: Enable SSL in Nginx

Once the certificate is obtained, activate the SSL configuration:

1. Copy the SSL template into the frontend Nginx config:
```bash
cp nginx/nginx-ssl.conf.template frontend/nginx.conf
```

2. Rebuild and restart the frontend container:
```bash
docker compose up -d --build frontend
```

Now open **`https://assetra.shareindiainsurance.com`** in your browser.
You will see the green padlock and the full Assetra application running securely with HTTPS!

---

## Step 11: Create the First Administrator Account

Seed the initial administrator account inside the running backend container:
```bash
docker compose exec backend python seed_admin.py
```
Follow the interactive prompt to set the admin email and password.

---

## Step 12: Set Up Automatic SSL Renewal

Certificates expire every 90 days. Set up a daily cron job to renew them automatically:
```bash
# Open crontab editor
sudo crontab -e
```

Add the following line to the end of the file:
```cron
0 3 * * * certbot renew --webroot -w /var/www/certbot --quiet && docker compose -f /home/ubuntu/Assetra/docker-compose.yml restart frontend
```
This runs daily at 3:00 AM, automatically renews any certificate within 30 days of expiry, and reloads Nginx.

---

## Useful Operational Commands

### View Live Logs:
```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Frontend/Nginx only
docker compose logs -f frontend

# Database only
docker compose logs -f db
```

### Restart Application:
```bash
docker compose restart
```

### Pull Updates from GitHub and Redeploy:
```bash
cd /home/ubuntu/Assetra
git pull origin main
docker compose up -d --build
```

### Database Backup:
```bash
docker compose exec db mysqldump -u far_user -p far_app > backup_$(date +%F).sql
```
