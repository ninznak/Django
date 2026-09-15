#!/bin/bash
# update-safe.sh — deploy с автоматическим бэкапом БД ДО миграций.
# Позволяет безопасно катать обновления, когда часть статей (и других данных)
# живёт только на проде (добавлено/отредактировано через Django admin),
# а часть приходит через код (миграции / management-команды).
#
# Что делает:
#   1. Бэкап БД в /var/backups/creativesphere/: тип определяется по .env —
#      DJANGO_DATABASE=postgresql → pg_dump (db-<ts>.dump), иначе SQLite →
#      консистентная копия файла (db-<ts>.sqlite3, через Python backup API).
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
#   DB connection settings are read from Django, including .env.
#   BACKUP_DIR       — куда складывать дампы (по умолчанию /var/backups/creativesphere)
#   BACKUP_KEEP      — сколько последних дампов хранить (по умолчанию 30)
#   SKIP_DB_BACKUP=1 — пропустить бэкап БД (НЕ рекомендуется)

set -eo pipefail
umask 077

PROJECT_DIR="${1:-/var/www/Django}"
VENV_DIR="$PROJECT_DIR/venv"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/creativesphere}"
BACKUP_KEEP="${BACKUP_KEEP:-30}"
STAMP="$(date +%F-%H%M%S)"
LOG_FILE="$PROJECT_DIR/deploy/update-safe.log"

mkdir -p "$PROJECT_DIR/deploy"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE"
}

# Read effective database settings through Django, including python-dotenv.
log "Safe deploy: $PROJECT_DIR"
if [ "${SKIP_DB_BACKUP:-0}" != "1" ]; then
    if DB_BACKUP=$(cd "$PROJECT_DIR" && "$VENV_DIR/bin/python" manage.py backup_database --directory "$BACKUP_DIR" --keep "$BACKUP_KEEP"); then
        log "Database backup OK: $DB_BACKUP"
    else
        log "Database backup failed; deployment stopped."
        exit 1
    fi
else
    log "SKIP_DB_BACKUP=1 — backup explicitly skipped"
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
