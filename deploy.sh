#!/bin/bash
# ==============================================================================
# FlexyRide Corporate - Production Deployment Script
# Supports: Ubuntu/Debian, Nginx, Gunicorn/Uvicorn (ASGI), Redis, Celery, Cloudflare Strict SSL
# Target Host: test-corporate.flexyridegh.com
# ==============================================================================

set -e

# Configuration
PROJECT_NAME="flexyride-corporate"
DOMAIN="test-corporate.flexyridegh.com"
USER="${SUDO_USER:-patmac}"
[ "$USER" = "root" ] && USER="patmac"

PROJECT_DIR="/opt/$PROJECT_NAME"
GUNICORN_WORKERS=3

echo "========================================================="
echo "Starting deployment for $PROJECT_NAME on $DOMAIN"
echo "Project Directory: $PROJECT_DIR"
echo "System User:       $USER"
echo "========================================================="

# 1. Update system and install system dependencies
echo "=> Updating system and installing dependencies..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv nginx curl ufw redis-server

# Ensure Redis is running for Celery and caching
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 2. Setup Project Directory in /opt
echo "=> Setting up project directory in $PROJECT_DIR..."
sudo mkdir -p "$PROJECT_DIR"

# If script is run from a cloned repo folder outside /opt, copy files over
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$SCRIPT_DIR" != "$PROJECT_DIR" ] && [ -f "$SCRIPT_DIR/manage.py" ]; then
    echo "=> Copying project files from $SCRIPT_DIR to $PROJECT_DIR..."
    sudo cp -ru "$SCRIPT_DIR"/. "$PROJECT_DIR"/
fi

sudo chown -R "$USER:$USER" "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 3. Create Virtual Environment and Install Requirements
echo "=> Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip

# Install project requirements if file exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Core production servers & worker dependencies
pip install gunicorn uvicorn[standard] daphne setproctitle redis celery django-redis requests

# 4. Django setup (Migrations, Static files)
echo "=> Running Django setup tasks..."
sudo mkdir -p "$PROJECT_DIR/staticfiles"
python manage.py makemigrations --noinput || true
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 4b. Set correct file/folder permissions
echo "=> Setting file and folder permissions..."

# -- staticfiles: readable by Nginx (www-data), owned by app user
sudo chown -R "$USER:www-data" "$PROJECT_DIR/staticfiles"
sudo chmod -R 755 "$PROJECT_DIR/staticfiles"

# -- media: readable & writable by app user, readable by Nginx (www-data)
sudo mkdir -p "$PROJECT_DIR/media"
sudo chown -R "$USER:www-data" "$PROJECT_DIR/media"
sudo chmod -R 775 "$PROJECT_DIR/media"

# -- db.sqlite3 (if using SQLite): readable/writable by app user
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    sudo chown "$USER:$USER" "$PROJECT_DIR/db.sqlite3"
    sudo chmod 660 "$PROJECT_DIR/db.sqlite3"
fi

# Ensure project directory is traversable by Gunicorn and Nginx
sudo chown "$USER:www-data" "$PROJECT_DIR"
sudo chmod 750 "$PROJECT_DIR"

# 5. Setup Gunicorn Systemd Service (ASGI / Uvicorn for WebSockets + HTTP)
echo "=> Configuring Gunicorn ASGI service..."
sudo bash -c "cat > /etc/systemd/system/gunicorn_${PROJECT_NAME}.service << EOF
[Unit]
Description=Gunicorn ASGI daemon for $PROJECT_NAME
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=\"PATH=$PROJECT_DIR/venv/bin\"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker --access-logfile - --workers $GUNICORN_WORKERS --bind unix:$PROJECT_DIR/$PROJECT_NAME.sock flexyride_corporate.asgi:application

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable "gunicorn_${PROJECT_NAME}"
sudo systemctl restart "gunicorn_${PROJECT_NAME}"

# 5b. Setup Celery Worker Systemd Service
echo "=> Configuring Celery Worker service..."
sudo bash -c "cat > /etc/systemd/system/celery_${PROJECT_NAME}.service << EOF
[Unit]
Description=Celery Worker for $PROJECT_NAME
After=network.target redis-server.service

[Service]
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=\"PATH=$PROJECT_DIR/venv/bin\"
ExecStart=$PROJECT_DIR/venv/bin/celery -A flexyride_corporate worker -l info --concurrency=4 -Q default,high_priority,celery
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

# 5c. Setup Celery Beat Systemd Service (Scheduled tasks: recurring journeys, compliance alerts, SLA)
echo "=> Configuring Celery Beat scheduler service..."
sudo bash -c "cat > /etc/systemd/system/celerybeat_${PROJECT_NAME}.service << EOF
[Unit]
Description=Celery Beat Scheduler for $PROJECT_NAME
After=network.target redis-server.service

[Service]
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment=\"PATH=$PROJECT_DIR/venv/bin\"
ExecStart=$PROJECT_DIR/venv/bin/celery -A flexyride_corporate beat -l info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable "celery_${PROJECT_NAME}"
sudo systemctl restart "celery_${PROJECT_NAME}"
sudo systemctl enable "celerybeat_${PROJECT_NAME}"
sudo systemctl restart "celerybeat_${PROJECT_NAME}"

# 6. Setup Cloudflare SSL Certificates (Strict Mode)
echo "=> Configuring Cloudflare SSL certificates..."

# Automatically detect existing certs from another project on this server
if [ -s "/etc/ssl/cloudflare/origin.pem" ] && [ -s "/etc/ssl/cloudflare/origin-key.pem" ]; then
    SSL_CERT="/etc/ssl/cloudflare/origin.pem"
    SSL_KEY="/etc/ssl/cloudflare/origin-key.pem"
    echo "✓ Reusing existing Cloudflare Origin Certificate found at /etc/ssl/cloudflare/"
elif [ -s "/etc/nginx/ssl/origin.pem" ] && [ -s "/etc/nginx/ssl/origin-key.pem" ]; then
    SSL_CERT="/etc/nginx/ssl/origin.pem"
    SSL_KEY="/etc/nginx/ssl/origin-key.pem"
    echo "✓ Reusing existing Cloudflare Origin Certificate found at /etc/nginx/ssl/"
elif [ -s "/etc/nginx/ssl/$DOMAIN.pem" ] && [ -s "/etc/nginx/ssl/$DOMAIN.key" ]; then
    SSL_CERT="/etc/nginx/ssl/$DOMAIN.pem"
    SSL_KEY="/etc/nginx/ssl/$DOMAIN.key"
    echo "✓ Reusing existing certificate for $DOMAIN at /etc/nginx/ssl/"
else
    SSL_CERT="/etc/ssl/cloudflare/origin.pem"
    SSL_KEY="/etc/ssl/cloudflare/origin-key.pem"
    sudo mkdir -p /etc/ssl/cloudflare
    echo ""
    echo "========================================================="
    echo "  STEP: Paste your Cloudflare ORIGIN CERTIFICATE below."
    echo "  Go to Cloudflare Dashboard → SSL/TLS → Origin Server"
    echo "  → Create Certificate (Hostnames: *.flexyridegh.com, flexyridegh.com)"
    echo "  Paste it here, then press ENTER and Ctrl+D when done:"
    echo "========================================================="
    sudo bash -c "cat > $SSL_CERT"
    echo "✓ Certificate saved."

    echo ""
    echo "========================================================="
    echo "  STEP: Paste your Cloudflare PRIVATE KEY below."
    echo "  (Shown once when you created the cert in Cloudflare)"
    echo "  Paste it here, then press ENTER and Ctrl+D when done:"
    echo "========================================================="
    sudo bash -c "cat > $SSL_KEY"
    sudo chmod 400 "$SSL_KEY"
    echo "✓ Private key saved and locked (chmod 400)."
fi

# Cloudflare Authenticated Origin Pulls CA
echo "=> Downloading Cloudflare Authenticated Origin Pull CA..."
sudo mkdir -p /etc/nginx/ssl
sudo curl -s https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem -o /etc/nginx/ssl/cloudflare_origin_pull_ca.pem
echo "✓ Cloudflare Origin Pull CA saved."

# 7. Setup Nginx with Cloudflare Security
echo "=> Configuring Nginx..."
sudo bash -c "cat > /etc/nginx/sites-available/$PROJECT_NAME << EOF
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\\\$server_name\\\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # Cloudflare Strict SSL (Reusing Server Certificate)
    ssl_certificate $SSL_CERT;
    ssl_certificate_key $SSL_KEY;
    
    # Authenticated Origin Pulls (only Cloudflare edge can talk to origin)
    ssl_client_certificate /etc/nginx/ssl/cloudflare_origin_pull_ca.pem;
    ssl_verify_client on;

    # SSL Security Enhancements
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header X-Frame-Options \"SAMEORIGIN\" always;
    add_header X-XSS-Protection \"1; mode=block\" always;
    add_header X-Content-Type-Options \"nosniff\" always;
    add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;

    # Cloudflare Real IP Handling
    set_real_ip_from 173.245.48.0/20;
    set_real_ip_from 103.21.244.0/22;
    set_real_ip_from 103.22.200.0/22;
    set_real_ip_from 103.31.4.0/22;
    set_real_ip_from 141.101.64.0/18;
    set_real_ip_from 108.162.192.0/18;
    set_real_ip_from 190.93.240.0/20;
    set_real_ip_from 188.114.96.0/20;
    set_real_ip_from 197.234.240.0/22;
    set_real_ip_from 198.41.128.0/17;
    set_real_ip_from 162.158.0.0/15;
    set_real_ip_from 104.16.0.0/13;
    set_real_ip_from 104.24.0.0/14;
    set_real_ip_from 172.64.0.0/13;
    set_real_ip_from 131.0.72.0/22;
    set_real_ip_from 2400:cb00::/32;
    set_real_ip_from 2606:4700::/32;
    set_real_ip_from 2803:f800::/32;
    set_real_ip_from 2405:b500::/32;
    set_real_ip_from 2405:8100::/32;
    set_real_ip_from 2a06:98c0::/29;
    set_real_ip_from 2c0f:f248::/32;
    real_ip_header CF-Connecting-IP;

    client_max_body_size 100M;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control \"public, no-transform\";
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 30d;
        add_header Cache-Control \"public, no-transform\";
    }

    # WebSocket Upgrade Handling (Live tracking, status updates)
    location /ws/ {
        proxy_pass http://unix:$PROJECT_DIR/$PROJECT_NAME.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\\$http_upgrade;
        proxy_set_header Connection \"upgrade\";
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_set_header X-Forwarded-Host \\\$host;
        proxy_set_header X-Forwarded-Port \\\$server_port;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Main Corporate Portal, Admin & REST API
    location / {
        proxy_pass http://unix:$PROJECT_DIR/$PROJECT_NAME.sock;
        proxy_http_version 1.1;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
        proxy_set_header X-Forwarded-Host \\\$host;
        proxy_set_header X-Forwarded-Port \\\$server_port;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF"

sudo ln -sf "/etc/nginx/sites-available/$PROJECT_NAME" /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 8. Fix Nginx → Gunicorn socket permissions
echo "=> Fixing socket permissions for Nginx..."
sudo usermod -a -G "$USER" www-data
sudo chmod g+x "/home/$USER" || true
echo "✓ www-data added to group '$USER' and user home directory made traversable."

# 9. Setup UFW Firewall
echo "=> Setting up UFW firewall..."
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH

echo "========================================================="
echo "🎉 Deployment setup complete for FlexyRide Corporate!"
echo "========================================================="
echo "Domain:      https://$DOMAIN"
echo "Project Dir: $PROJECT_DIR"
echo ""
echo "Service Management Commands:"
echo "  - Gunicorn App:     sudo systemctl status gunicorn_${PROJECT_NAME}"
echo "  - Celery Worker:    sudo systemctl status celery_${PROJECT_NAME}"
echo "  - Celery Beat:      sudo systemctl status celerybeat_${PROJECT_NAME}"
echo "  - Restart All App:  sudo systemctl restart gunicorn_${PROJECT_NAME} celery_${PROJECT_NAME} celerybeat_${PROJECT_NAME}"
echo "  - Restart Nginx:    sudo systemctl restart nginx"
echo ""
echo "Next Steps:"
echo "1. Verify SSL cert is active at $SSL_CERT"
echo "2. Ensure Cloudflare DNS A Record points 'test-corporate' to your server IP"
echo "3. Ensure Cloudflare SSL is set to 'Full (strict)' and Authenticated Origin Pulls is ON"
echo "4. In .env set ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1"
echo "========================================================="
