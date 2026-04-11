#!/bin/bash
# update.sh — скрипт быстрого обновления проекта на VPS
# Использование: sudo bash scripts/update.sh

set -e

PROJECT_DIR="/var/www/Django"
VENV_DIR="$PROJECT_DIR/venv"
LOG_FILE="/var/log/django-update.log"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE"
}

log "=========================================="
log "🚀 Начало обновления CreativeSphere"
log "=========================================="

# Переход в директорию проекта
cd "$PROJECT_DIR" || { log "❌ Ошибка: не удалось перейти в $PROJECT_DIR"; exit 1; }

# 1. Получение свежих изменений из Git
log "📥 Git pull..."
if git pull 2>&1 | tee -a "$LOG_FILE"; then
    log "✅ Git pull завершён успешно"
else
    log "❌ Ошибка Git pull"
    exit 1
fi

# 2. Исправление прав доступа
log "🔐 Исправление прав доступа..."
chown -R www-data:www-data "$PROJECT_DIR"
log "✅ Права доступа обновлены"

# 3. Активация venv и применение изменений
log "📦 Установка зависимостей..."
sudo -u www-data bash -c "
  cd $PROJECT_DIR
  source $VENV_DIR/bin/activate
  pip install -r requirements.txt 2>&1 | tee -a $LOG_FILE
"
log "✅ Зависимости обновлены"

log "🗄️ Применение миграций БД..."
sudo -u www-data bash -c "
  cd $PROJECT_DIR
  source $VENV_DIR/bin/activate
  python manage.py migrate --noinput 2>&1 | tee -a $LOG_FILE
"
log "✅ Миграции применены"

log "🖼️ Сбор статики..."
sudo -u www-data bash -c "
  cd $PROJECT_DIR
  source $VENV_DIR/bin/activate
  python manage.py collectstatic --noinput 2>&1 | tee -a $LOG_FILE
"
log "✅ Статика собрана"

# 4. Перезапуск Gunicorn
log "🔄 Перезапуск Gunicorn..."
if systemctl restart creativesphere-gunicorn; then
    log "✅ Gunicorn перезапущен"
else
    log "❌ Ошибка перезапуска Gunicorn"
    exit 1
fi

# 5. Проверка статуса службы
log "📊 Проверка статуса службы..."
systemctl is-active creativesphere-gunicorn > /dev/null && log "✅ Служба активна" || log "⚠️ Служба неактивна"

log "=========================================="
log "🎉 Обновление завершено успешно!"
log "=========================================="
log "📄 Полный лог: $LOG_FILE"
log "📊 Логи службы: sudo journalctl -u creativesphere-gunicorn -f"

echo ""
echo "✅ Обновление завершено!"
echo "📄 Лог файл: $LOG_FILE"
