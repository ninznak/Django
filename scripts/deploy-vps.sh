#!/usr/bin/env bash
set -euo pipefail

# One-shot deploy for CreativeSphere Django on Ubuntu/Debian VPS
#
# Usage:
#   sudo bash scripts/deploy-vps.sh <primary-domain> <app-dir> [extra-apex ...]
#
# Examples:
#   sudo bash scripts/deploy-vps.sh trally.ru /var/www/Django
#       → also enables kurilenkoart.ru on the same VPS (Nginx, Certbot, .env)
#   sudo env DEPLOY_SINGLE_DOMAIN=1 bash scripts/deploy-vps.sh trally.ru /var/www/Django
#       → only trally.ru (no kurilenkoart.ru)
#   sudo bash scripts/deploy-vps.sh kurilenkoart.ru /var/www/Django trally.ru
#
# Env:
#   LETSENCRYPT_EMAIL — optional, for Certbot expiry notices
#   DEPLOY_EXTRA_DOMAINS — space-separated apices (optional)
#   DEPLOY_SINGLE_DOMAIN=1 — with primary trally.ru, do not auto-add kurilenkoart.ru
#
# Prerequisites: DNS A records for every apex (and www) → this server; ports 22, 80, 443 open.

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run with sudo/root."
  exit 1
fi

PRIMARY="${1:-}"
APP_DIR="${2:-/var/www/Django}"
shift 2 || true

if [[ -z "${PRIMARY}" ]]; then
  echo "Usage: sudo bash $0 <primary-domain> <app-dir> [extra-apex ...]"
  echo "Example: sudo bash $0 trally.ru /var/www/Django"
  exit 1
fi

EXTRA_FROM_ARGS=( "$@" )
if [[ -n "${DEPLOY_EXTRA_DOMAINS:-}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_FROM_ENV=(${DEPLOY_EXTRA_DOMAINS})
  EXTRA_FROM_ARGS+=( "${EXTRA_FROM_ENV[@]}" )
fi

# Default second apex: kurilenkoart.ru when primary is trally.ru (prepare both on one VPS).
if [[ ${#EXTRA_FROM_ARGS[@]} -eq 0 && "${PRIMARY}" == "trally.ru" && "${DEPLOY_SINGLE_DOMAIN:-0}" != "1" ]]; then
  EXTRA_FROM_ARGS=( "kurilenkoart.ru" )
fi

ALL_APEX=( "${PRIMARY}" "${EXTRA_FROM_ARGS[@]}" )
# Deduplicate while keeping order
declare -A SEEN=()
UNIQUE_APEX=()
for d in "${ALL_APEX[@]}"; do
  [[ -z "${d}" ]] && continue
  if [[ -z "${SEEN[${d}]:-}" ]]; then
    SEEN["${d}"]=1
    UNIQUE_APEX+=( "${d}" )
  fi
done
ALL_APEX=( "${UNIQUE_APEX[@]}" )

SITE_DOMAINS_CSV=$(IFS=,; echo "${ALL_APEX[*]}")

SITE_NAME="creativesphere-gunicorn"
UNIT_PATH="/etc/systemd/system/${SITE_NAME}.service"
NGINX_AVAILABLE="/etc/nginx/sites-available/creativesphere-django"
NGINX_ENABLED="/etc/nginx/sites-enabled/creativesphere-django"

if [[ ! -d "${APP_DIR}" ]]; then
  echo "App directory not found: ${APP_DIR}"
  exit 1
fi

if [[ ! -f "${APP_DIR}/manage.py" ]]; then
  echo "manage.py not found in ${APP_DIR}. Use the Django project root."
  exit 1
fi

SERVER_NAMES=()
for d in "${ALL_APEX[@]}"; do
  SERVER_NAMES+=( "${d}" "www.${d}" )
done
SERVER_NAME_LINE="${SERVER_NAMES[*]}"

CERTBOT_DOMAINS=()
for d in "${ALL_APEX[@]}"; do
  CERTBOT_DOMAINS+=( -d "${d}" -d "www.${d}" )
done

echo "==> Domains (apex): ${ALL_APEX[*]}"
echo "    Canonical / PUBLIC_SITE_URL: https://${PRIMARY}"

echo "==> Updating system packages"
apt-get update
apt-get upgrade -y

echo "==> Installing Python, Nginx, Certbot"
apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

echo "==> Python venv and dependencies"
cd "${APP_DIR}"
python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

SECRET_KEY="${DJANGO_SECRET_KEY:-}"
if [[ -z "${SECRET_KEY}" ]]; then
  SECRET_KEY="$(openssl rand -base64 48 | tr -d '\n' | tr '/+' '_-')"
fi

echo "==> Writing ${APP_DIR}/.env"
cat > "${APP_DIR}/.env" <<EOF
DJANGO_SECRET_KEY=${SECRET_KEY}
DEBUG=0
DJANGO_SITE_DOMAINS=${SITE_DOMAINS_CSV}
DJANGO_CANONICAL_DOMAIN=${PRIMARY}
PUBLIC_SITE_URL=https://${PRIMARY}
EOF
chmod 600 "${APP_DIR}/.env"

echo "==> File ownership for www-data (Gunicorn user)"
chown -R www-data:www-data "${APP_DIR}"

echo "==> Django migrate, collectstatic"
export DJANGO_SETTINGS_MODULE=creativesphere.settings
sudo -u www-data bash -c "
  set -e
  cd '${APP_DIR}'
  source venv/bin/activate
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
"

echo "==> systemd: Gunicorn (${SITE_NAME})"
cat > "${UNIT_PATH}" <<EOF
[Unit]
Description=CreativeSphere Django (Gunicorn)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=${APP_DIR}
Environment=DJANGO_SETTINGS_MODULE=creativesphere.settings
ExecStart=${APP_DIR}/venv/bin/gunicorn \\
    --bind 127.0.0.1:8000 \\
    --workers 3 \\
    --timeout 120 \\
    --access-logfile - \\
    --error-logfile - \\
    creativesphere.wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SITE_NAME}"
systemctl restart "${SITE_NAME}"

echo "==> Nginx (HTTP first)"
# shellcheck disable=SC2086
cat > "${NGINX_AVAILABLE}" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${SERVER_NAME_LINE};

    client_max_body_size 25M;

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location /media/ {
        alias ${APP_DIR}/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf "${NGINX_AVAILABLE}" "${NGINX_ENABLED}"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
systemctl enable nginx

echo "==> Let's Encrypt SSL (HTTPS redirect)"
CERT_EMAIL="${LETSENCRYPT_EMAIL:-admin@${PRIMARY}}"
set +e
certbot --nginx "${CERTBOT_DOMAINS[@]}" \
    --non-interactive --agree-tos -m "${CERT_EMAIL}" --redirect
CERT_EXIT=$?
set -e
if [[ "${CERT_EXIT}" -ne 0 ]]; then
  echo "Certbot failed. Ensure DNS for all names points to this VPS, then run e.g.:"
  echo "  sudo certbot --nginx ${CERTBOT_DOMAINS[*]} --redirect"
  exit 1
fi

systemctl restart "${SITE_NAME}"

echo "==> Done"
echo "Primary URL (canonical for SEO): https://${PRIMARY}"
echo "Also accepted: ${ALL_APEX[*]}"
echo "App logs: journalctl -u ${SITE_NAME} -f"
echo "Restart app: sudo systemctl restart ${SITE_NAME}"
