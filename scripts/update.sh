#!/bin/bash
# update.sh — quick deploy: git pull → deps → migrate → collectstatic → restart Gunicorn
# Usage: sudo bash scripts/update.sh [PROJECT_DIR]
# Default project: /var/www/Django
#
# Env (optional):
#   GIT_BRANCH          — ветка remote (по умолчанию main)
#   GUNICORN_SERVICE    — имя systemd unit Gunicorn (по умолчанию creativesphere-gunicorn)

set -eo pipefail

PROJECT_DIR="${1:-/var/www/Django}"
VENV_DIR="$PROJECT_DIR/venv"
GIT_BRANCH="${GIT_BRANCH:-main}"
GUNICORN_SERVICE="${GUNICORN_SERVICE:-creativesphere-gunicorn}"
mkdir -p "$PROJECT_DIR/deploy"
LOG_FILE="$PROJECT_DIR/deploy/update.log"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE"
}

log "=========================================="
log "Начало обновления CreativeSphere"
log "=========================================="

cd "$PROJECT_DIR" || { log "Ошибка: не удалось перейти в $PROJECT_DIR"; exit 1; }

# Git 2.35+: repo owned by www-data but pull runs as root → mark safe once per root
if ! git config --global --get-all safe.directory | grep -Fxq "$PROJECT_DIR"; then
    git config --global --add safe.directory "$PROJECT_DIR"
    log "Добавлен safe.directory для $PROJECT_DIR"
fi

# 1. Git pull (pipefail: failure не маскируется tee)
log "Git pull origin $GIT_BRANCH..."
if git pull origin "$GIT_BRANCH" 2>&1 | tee -a "$LOG_FILE"; then
    log "Git pull завершён успешно"
else
    log "Ошибка Git pull — обновление прервано"
    exit 1
fi

# 2. Права для веб-пользователя
log "Права доступа www-data..."
chown -R www-data:www-data "$PROJECT_DIR"
log "Права обновлены"

# 3. venv: pip / migrate / collectstatic (вывод в лог от имени root >>)
log "Установка зависимостей..."
if sudo -u www-data bash -c "
    set -e
    cd '$PROJECT_DIR'
    source '$VENV_DIR/bin/activate'
    pip install -r requirements.txt
" >>"$LOG_FILE" 2>&1; then
    log "Зависимости обновлены"
else
    log "Ошибка pip install"
    exit 1
fi

log "Миграции БД..."
if sudo -u www-data bash -c "
    set -e
    cd '$PROJECT_DIR'
    source '$VENV_DIR/bin/activate'
    python manage.py migrate --noinput
" >>"$LOG_FILE" 2>&1; then
    log "Миграции применены"
else
    log "Ошибка migrate"
    exit 1
fi

log "Collectstatic..."
if sudo -u www-data bash -c "
    set -e
    cd '$PROJECT_DIR'
    source '$VENV_DIR/bin/activate'
    python manage.py collectstatic --noinput
" >>"$LOG_FILE" 2>&1; then
    log "Статика собрана"
else
    log "Ошибка collectstatic"
    exit 1
fi

log "Перезапуск $GUNICORN_SERVICE..."
if systemctl restart "$GUNICORN_SERVICE"; then
    log "Gunicorn перезапущен"
else
    log "Ошибка systemctl restart"
    exit 1
fi

systemctl is-active "$GUNICORN_SERVICE" >/dev/null && log "Служба активна" || log "Внимание: служба не active"

log "=========================================="
log "Обновление завершено успешно"
log "=========================================="
log "Лог: $LOG_FILE"
log "Журнал: journalctl -u $GUNICORN_SERVICE -f"

echo ""
echo "Готово. Лог: $LOG_FILE"
