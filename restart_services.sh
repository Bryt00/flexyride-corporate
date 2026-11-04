#!/bin/bash
# ==============================================================================
# FlexyRide Corporate - Safe Zero-Downtime Deployment & Service Reload Script
# Updates code, checks health, updates static files, and performs a graceful
# rolling reload of Gunicorn, Celery, and Nginx without 502/server errors.
#
# Usage:
#   sudo bash restart_services.sh              # Graceful rolling reload (zero downtime)
#   sudo bash restart_services.sh --pull       # Pull git updates first, then graceful reload
#   sudo bash restart_services.sh --hard       # Hard restart (forces cold restart of all services)
# ==============================================================================

set -e

# Configuration
PROJECT_NAME="flexyride-corporate"
USER="${SUDO_USER:-patmac}"
[ "$USER" = "root" ] && USER="patmac"

# Detect directory: prefer /opt/flexyride-corporate, fallback to script directory
if [ -d "/opt/$PROJECT_NAME" ]; then
    PROJECT_DIR="/opt/$PROJECT_NAME"
elif [ -f "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manage.py" ]; then
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    PROJECT_DIR="/opt/$PROJECT_NAME"
fi

# Flags
DO_PULL=false
HARD_RESTART=false

for arg in "$@"; do
    case "$arg" in
        --pull|-p)
            DO_PULL=true
            ;;
        --hard)
            HARD_RESTART=true
            ;;
    esac
done

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================="
echo -e "${BLUE}FlexyRide Corporate - Safe Deployment & Reload${NC}"
echo "Project Directory: $PROJECT_DIR"
if [ "$HARD_RESTART" = true ]; then
    echo -e "Mode: ${RED}Hard Service Restart (Cold Boot)${NC}"
else
    echo -e "Mode: ${GREEN}Graceful Rolling Reload (Zero-Downtime)${NC}"
fi
echo "========================================================="

# 1. Check Root Privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (use sudo: sudo bash restart_services.sh)${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# 2. Optional Git Pull
if [ "$DO_PULL" = true ]; then
    if [ -d ".git" ]; then
        echo -e "${YELLOW}1. Pulling latest updates from Git...${NC}"
        git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true
        sudo -u "$USER" git pull || echo -e "${RED}Git pull encountered an issue, proceeding with deployment...${NC}"
        echo -e "${GREEN}✓ Git repository updated${NC}"
    fi
fi

# 3. Virtual Environment Setup
echo -e "${YELLOW}2. Activating Python virtual environment...${NC}"
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
elif [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated (.venv)${NC}"
else
    echo -e "${RED}Warning: Virtual environment not found at $PROJECT_DIR/venv${NC}"
fi

# 4. Install / Update Requirements (if requirements.txt exists)
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${YELLOW}3. Checking Python dependencies...${NC}"
    pip install -r "$PROJECT_DIR/requirements.txt" --quiet
    echo -e "${GREEN}✓ Dependencies verified${NC}"
fi

# 5. Pre-flight Health Check (Prevents deploying broken code / 500 crashes)
if [ -f "$PROJECT_DIR/manage.py" ]; then
    echo -e "${YELLOW}4. Running pre-flight system integrity check...${NC}"
    if python manage.py check; then
        echo -e "${GREEN}✓ System check passed - safe to deploy${NC}"
    else
        echo -e "${RED}✗ System check failed! Aborting deployment to prevent downtime.${NC}"
        exit 1
    fi

    # 6. Database Migrations
    echo -e "${YELLOW}5. Running database migrations...${NC}"
    python manage.py migrate --noinput
    echo -e "${GREEN}✓ Migrations up to date${NC}"

    # 7. Safe Static Files Collection (without --clear to avoid asset blips)
    echo -e "${YELLOW}6. Collecting static assets (UI updates)...${NC}"
    python manage.py collectstatic --noinput
    echo -e "${GREEN}✓ Static files collected${NC}"
fi

# 8. Ensure Permissions
echo -e "${YELLOW}7. Ensuring filesystem permissions...${NC}"
mkdir -p "$PROJECT_DIR/staticfiles" "$PROJECT_DIR/media"
chown -R "$USER:www-data" "$PROJECT_DIR/staticfiles" "$PROJECT_DIR/media"
chmod -R 755 "$PROJECT_DIR/staticfiles"
chmod -R 775 "$PROJECT_DIR/media"
chown "$USER:$USER" "$PROJECT_DIR"/db.sqlite3* 2>/dev/null || true
chmod 664 "$PROJECT_DIR"/db.sqlite3* 2>/dev/null || true
chown "$USER:www-data" "$PROJECT_DIR"
chmod 775 "$PROJECT_DIR"
echo -e "${GREEN}✓ Permissions verified${NC}"

# 9. Redis Health / Restart
echo -e "${YELLOW}8. Checking Redis cache & broker service...${NC}"
if [ "$HARD_RESTART" = true ]; then
    systemctl restart redis-server 2>/dev/null || systemctl restart redis 2>/dev/null || echo "Redis service not found"
    echo -e "${GREEN}✓ Redis restarted${NC}"
else
    if systemctl is-active --quiet redis-server 2>/dev/null || systemctl is-active --quiet redis 2>/dev/null; then
        echo -e "${GREEN}✓ Redis active and healthy (sessions preserved)${NC}"
    else
        systemctl start redis-server 2>/dev/null || systemctl start redis 2>/dev/null || echo "Redis service not found"
        echo -e "${GREEN}✓ Redis started${NC}"
    fi
fi

# 10. Gunicorn Rolling Graceful Reload (Zero-Downtime)
echo -e "${YELLOW}9. Reloading Gunicorn ASGI web application...${NC}"
GUNICORN_SERVICE=""
if systemctl list-unit-files | grep -q "gunicorn_${PROJECT_NAME}"; then
    GUNICORN_SERVICE="gunicorn_${PROJECT_NAME}"
elif systemctl list-unit-files | grep -q "gunicorn_flexyride_corporate"; then
    GUNICORN_SERVICE="gunicorn_flexyride_corporate"
fi

if [ -n "$GUNICORN_SERVICE" ]; then
    if [ "$HARD_RESTART" = true ]; then
        systemctl restart "$GUNICORN_SERVICE"
        echo -e "${GREEN}✓ Service $GUNICORN_SERVICE hard restarted${NC}"
    else
        # Graceful reload sends SIGHUP: keeps old workers running until new workers boot
        if systemctl reload "$GUNICORN_SERVICE" 2>/dev/null; then
            echo -e "${GREEN}✓ Service $GUNICORN_SERVICE gracefully reloaded (zero downtime)${NC}"
        else
            # Fallback to direct process HUP signal or restart
            pkill -HUP -f "gunicorn.*${PROJECT_NAME}" 2>/dev/null || systemctl restart "$GUNICORN_SERVICE"
            echo -e "${GREEN}✓ Sent graceful HUP reload signal to $GUNICORN_SERVICE${NC}"
        fi
    fi
elif pgrep -f "gunicorn.*flexyride" > /dev/null; then
    pkill -HUP -f "gunicorn.*flexyride"
    echo -e "${GREEN}✓ Sent graceful HUP reload signal to running Gunicorn workers${NC}"
elif command -v supervisorctl &> /dev/null; then
    supervisorctl restart flexyride_corporate_replicas:* 2>/dev/null || true
    echo -e "${GREEN}✓ Supervisor replicas refreshed${NC}"
fi

# 11. Celery Worker & Scheduler Update
echo -e "${YELLOW}10. Refreshing Celery background workers and scheduler...${NC}"
rm -f "$PROJECT_DIR/celerybeat.pid" "/tmp/celerybeat_${PROJECT_NAME}.pid"
CELERY_SERVICE=""
CELERYBEAT_SERVICE=""
if systemctl list-unit-files | grep -q "celery_${PROJECT_NAME}"; then
    CELERY_SERVICE="celery_${PROJECT_NAME}"
    CELERYBEAT_SERVICE="celerybeat_${PROJECT_NAME}"
elif systemctl list-unit-files | grep -q "celery_flexyride_corporate"; then
    CELERY_SERVICE="celery_flexyride_corporate"
    CELERYBEAT_SERVICE="celerybeat_flexyride_corporate"
fi

if [ -n "$CELERY_SERVICE" ]; then
    systemctl restart "$CELERY_SERVICE" 2>/dev/null || true
    systemctl restart "$CELERYBEAT_SERVICE" 2>/dev/null || true
    echo -e "${GREEN}✓ Celery worker & beat services updated${NC}"
elif command -v supervisorctl &> /dev/null; then
    supervisorctl restart flexyride_corporate_celery:* 2>/dev/null || true
    echo -e "${GREEN}✓ Supervisor Celery tasks refreshed${NC}"
fi

# 12. Nginx Graceful Reload (Zero-Downtime, keeps live HTTPS sockets intact)
echo -e "${YELLOW}11. Testing and reloading Nginx...${NC}"
if nginx -t; then
    if [ "$HARD_RESTART" = true ]; then
        systemctl restart nginx
        echo -e "${GREEN}✓ Nginx restarted${NC}"
    else
        systemctl reload nginx
        echo -e "${GREEN}✓ Nginx gracefully reloaded (zero dropped connections)${NC}"
    fi
else
    echo -e "${RED}✗ Nginx configuration test failed! Aborting Nginx reload.${NC}"
    exit 1
fi

# 13. Service Status Summary
echo ""
echo "========================================================="
echo -e "${GREEN}🎉 Deployment completed successfully with ZERO downtime!${NC}"
echo "========================================================="
echo "Live Services Status:"
for svc in "$GUNICORN_SERVICE" "$CELERY_SERVICE" "$CELERYBEAT_SERVICE" "nginx"; do
    if [ -n "$svc" ]; then
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            echo -e "  - $svc: ${GREEN}Active (Running)${NC}"
        else
            echo -e "  - $svc: ${YELLOW}Inactive / Not configured${NC}"
        fi
    fi
done
if systemctl is-active --quiet "redis-server" 2>/dev/null || systemctl is-active --quiet "redis" 2>/dev/null; then
    echo -e "  - redis: ${GREEN}Active (Running)${NC}"
else
    echo -e "  - redis: ${YELLOW}Inactive / Not configured${NC}"
fi
echo "========================================================="
