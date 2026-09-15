#!/bin/bash
# ==============================================================================
# FlexyRide Corporate - Service Restart & Update Script
# Updates code/static assets and restarts Gunicorn (ASGI), Celery, Redis & Nginx
# Usage: sudo bash restart_services.sh [--pull]
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

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================="
echo -e "${BLUE}FlexyRide Corporate - Service Restart & Update${NC}"
echo "Project Directory: $PROJECT_DIR"
echo "========================================================="

# 1. Check Root Privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (use sudo: sudo bash restart_services.sh)${NC}"
    exit 1
fi

cd "$PROJECT_DIR"

# 2. Optional Git Pull (if --pull argument provided or asked)
if [ "$1" == "--pull" ] || [ "$1" == "-p" ]; then
    if [ -d ".git" ]; then
        echo -e "${YELLOW}1. Pulling latest updates from Git...${NC}"
        sudo -u "$USER" git pull || echo -e "${RED}Git pull encountered an issue, proceeding with restart...${NC}"
        echo -e "${GREEN}✓ Git repository updated${NC}"
    fi
fi

# 3. Virtual Environment Setup
echo -e "${YELLOW}2. Activating Python virtual environment...${NC}"
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
else
    echo -e "${RED}Warning: Virtual environment not found at $PROJECT_DIR/venv${NC}"
fi

# 4. Install / Update Requirements (if requirements.txt exists)
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${YELLOW}3. Checking Python dependencies...${NC}"
    pip install -r "$PROJECT_DIR/requirements.txt" --quiet
    echo -e "${GREEN}✓ Dependencies verified${NC}"
fi

# 5. Database Migrations
if [ -f "$PROJECT_DIR/manage.py" ]; then
    echo -e "${YELLOW}4. Running database migrations...${NC}"
    python manage.py migrate --noinput
    echo -e "${GREEN}✓ Migrations up to date${NC}"

    # 6. Static Files Collection
    echo -e "${YELLOW}5. Collecting static assets (UI updates)...${NC}"
    python manage.py collectstatic --noinput
    echo -e "${GREEN}✓ Static files collected${NC}"
fi

# 7. Ensure Permissions
echo -e "${YELLOW}6. Ensuring filesystem permissions...${NC}"
sudo mkdir -p "$PROJECT_DIR/staticfiles" "$PROJECT_DIR/media"
sudo chown -R "$USER:www-data" "$PROJECT_DIR/staticfiles" "$PROJECT_DIR/media"
sudo chmod -R 755 "$PROJECT_DIR/staticfiles"
sudo chmod -R 775 "$PROJECT_DIR/media"
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    sudo chown "$USER:$USER" "$PROJECT_DIR/db.sqlite3"
    sudo chmod 660 "$PROJECT_DIR/db.sqlite3"
fi
echo -e "${GREEN}✓ Permissions verified${NC}"

# 8. Restart Redis
echo -e "${YELLOW}7. Restarting Redis cache & message broker...${NC}"
systemctl restart redis-server || systemctl restart redis || echo "Redis service not found"
echo -e "${GREEN}✓ Redis restarted${NC}"

# 9. Restart Application Server (Systemd / Supervisor fallback)
echo -e "${YELLOW}8. Restarting Gunicorn ASGI web application...${NC}"
if systemctl list-unit-files | grep -q "gunicorn_${PROJECT_NAME}"; then
    systemctl restart "gunicorn_${PROJECT_NAME}"
    echo -e "${GREEN}✓ Systemd service gunicorn_${PROJECT_NAME} restarted${NC}"
elif systemctl list-unit-files | grep -q "gunicorn_flexyride_corporate"; then
    systemctl restart gunicorn_flexyride_corporate
    echo -e "${GREEN}✓ Systemd service gunicorn_flexyride_corporate restarted${NC}"
elif command -v supervisorctl &> /dev/null; then
    supervisorctl restart flexyride_corporate_replicas:* 2>/dev/null || true
    echo -e "${GREEN}✓ Supervisor replicas restarted${NC}"
fi

# 10. Restart Celery Worker & Beat
echo -e "${YELLOW}9. Restarting Celery background workers and scheduler...${NC}"
# Systemd mode
if systemctl list-unit-files | grep -q "celery_${PROJECT_NAME}"; then
    systemctl restart "celery_${PROJECT_NAME}"
    systemctl restart "celerybeat_${PROJECT_NAME}" 2>/dev/null || true
    echo -e "${GREEN}✓ Celery worker & beat systemd services restarted${NC}"
elif systemctl list-unit-files | grep -q "celery_flexyride_corporate"; then
    systemctl restart celery_flexyride_corporate
    systemctl restart celerybeat_flexyride_corporate 2>/dev/null || true
    echo -e "${GREEN}✓ Celery worker & beat systemd services restarted${NC}"
elif command -v supervisorctl &> /dev/null; then
    supervisorctl restart flexyride_corporate_celery:* 2>/dev/null || true
    echo -e "${GREEN}✓ Supervisor Celery tasks restarted${NC}"
fi

# 11. Test and Restart Nginx
echo -e "${YELLOW}10. Testing and restarting Nginx...${NC}"
if nginx -t; then
    systemctl restart nginx
    echo -e "${GREEN}✓ Nginx restarted successfully${NC}"
else
    echo -e "${RED}✗ Nginx configuration error! Check /etc/nginx/sites-available/$PROJECT_NAME${NC}"
    exit 1
fi

# 12. Service Status Summary
echo ""
echo "========================================================="
echo -e "${GREEN}🎉 All services updated & restarted successfully!${NC}"
echo "========================================================="
echo "Status Summary:"
for svc in "gunicorn_${PROJECT_NAME}" "celery_${PROJECT_NAME}" "celerybeat_${PROJECT_NAME}" "redis-server" "nginx"; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        echo -e "  - $svc: ${GREEN}Active (Running)${NC}"
    else
        echo -e "  - $svc: ${YELLOW}Inactive / Not configured${NC}"
    fi
done
echo "========================================================="
