#!/bin/bash
# update-safe.sh — deploy с автоматическим pg_dump-бэкапом ДО миграций.
# Позволяет безопасно катать обновления, когда часть статей (и других данных)
# живёт только на проде (добавлено/отредактировано через Django admin),
# а часть приходит через код (миграции / management-команды).
#
# Что делает:
#   1. pg_dump PostgreSQL-базы в /var/backups/creativesphere/<timestamp>.dump
#   2. Пишет снапшот core.NewsArticle в JSON (на случай, если нужна точечная
#      откатка только статей).
#   3. Вызывает обычный scripts/update.sh (git pull → pip → migrate →
#      collectstatic → restart).
#   4. В случае ошибки НИЧЕГО не откатывает автоматически — только показывает
#      путь до свежего дампа, чтобы вы могли восстановиться осознанно.
#
# Usage: sudo bash scripts/update-safe.sh [PROJECT_DIR]
# Default project: /var/www/Django
#
# Env (опционально):
#   POSTGRES_DB      — имя БД (по умолчанию creativesphere)
#   BACKUP_DIR       — куда складывать дампы (по умолчанию /var/backups/creativesphere)
#   BACKUP_KEEP      — сколько последних дампов хранить (по умолчанию 30)
#   SKIP_DB_BACKUP=1 — пропустить pg_dump (НЕ рекомендуется)

set -eo pipefail

PROJECT_DIR="${1:-/var/www/Django}"
VENV_DIR="$PROJECT_DIR/venv"
POSTGRES_DB="${POSTGRES_DB:-creativesphere}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/creativesphere}"
BACKUP_KEEP="${BACKUP_KEEP:-30}"
STAMP="$(date +%F-%H%M%S)"
LOG_FILE="$PROJECT_DIR/deploy/update-safe.log"

mkdir -p "$PROJECT_DIR/deploy"
mkdir -p "$BACKUP_DIR"
chown -R postgres:postgres "$BACKUP_DIR" 2>/dev/null || true

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE"
}

log "=========================================="
log "Safe deploy: $PROJECT_DIR (db=$POSTGRES_DB)"
log "=========================================="

# --- 1. pg_dump всей базы -----------------------------------------------
if [ "${SKIP_DB_BACKUP:-0}" != "1" ]; then
    DB_BACKUP="$BACKUP_DIR/db-$STAMP.dump"
    log "pg_dump -> $DB_BACKUP"
    if sudo -u postgres pg_dump -Fc -d "$POSTGRES_DB" -f "$DB_BACKUP"; then
        log "pg_dump OK ($(du -h "$DB_BACKUP" | cut -f1))"
    else
        log "ОШИБКА pg_dump — деплой прерван. Проверьте доступ к БД."
        exit 1
    fi

    # Оставляем только последние BACKUP_KEEP дампов
    ls -1t "$BACKUP_DIR"/db-*.dump 2>/dev/null \
        | tail -n +$((BACKUP_KEEP + 1)) \
        | xargs -r rm --
else
    log "SKIP_DB_BACKUP=1 — пропустил pg_dump (НЕ РЕКОМЕНДУЕТСЯ)"
fi

# --- 2. JSON-снапшот статей (маленький, удобен для точечной откатки) ---
NEWS_BACKUP="$BACKUP_DIR/news-$STAMP.json"
log "dumpdata core.NewsArticle -> $NEWS_BACKUP"
if sudo -u www-data bash -c "
    set -e
    cd '$PROJECT_DIR'
    source '$VENV_DIR/bin/activate'
    python manage.py dumpdata core.NewsArticle --indent 2
" > "$NEWS_BACKUP" 2>>"$LOG_FILE"; then
    log "Снапшот статей OK ($(wc -l < "$NEWS_BACKUP") строк)"
else
    log "Предупреждение: не удалось сохранить news-снапшот (возможно, таблицы ещё нет). Продолжаю."
    rm -f "$NEWS_BACKUP"
fi

# --- 3. Основной update.sh ----------------------------------------------
log "Вызов scripts/update.sh..."
if sudo bash "$PROJECT_DIR/scripts/update.sh" "$PROJECT_DIR"; then
    log "update.sh завершён успешно"
else
    RC=$?
    log "!!! update.sh упал с кодом $RC"
    log "!!! Свежий дамп БД: ${DB_BACKUP:-<не снят>}"
    log "!!! Снапшот статей: ${NEWS_BACKUP:-<не снят>}"
    log "!!! Для полного отката: см. блок \"Восстановление\" в AGENTS.md"
    exit $RC
fi

log "=========================================="
log "Safe deploy завершён. Дамп БД: ${DB_BACKUP:-skipped}"
log "=========================================="

echo ""
echo "Готово."
echo "  Лог:           $LOG_FILE"
echo "  Дамп БД:       ${DB_BACKUP:-<skipped>}"
echo "  Снапшот статей: ${NEWS_BACKUP:-<skipped>}"
