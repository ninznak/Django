#!/bin/bash
# update-safe.sh — deploy с автоматическим бэкапом БД ДО миграций.
# Позволяет безопасно катать обновления, когда часть статей (и других данных)
# живёт только на проде (добавлено/отредактировано через Django admin),
# а часть приходит через код (миграции / management-команды).
#
# Что делает:
#   1. Бэкап БД в /var/backups/creativesphere/: тип определяется по .env —
#      DJANGO_DATABASE=postgresql → pg_dump (db-<ts>.dump), иначе SQLite →
#      консистентная копия файла (db-<ts>.sqlite3, через sqlite3 .backup).
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
#   POSTGRES_DB      — имя Postgres-БД (по умолчанию creativesphere)
#   BACKUP_DIR       — куда складывать дампы (по умолчанию /var/backups/creativesphere)
#   BACKUP_KEEP      — сколько последних дампов хранить (по умолчанию 30)
#   SKIP_DB_BACKUP=1 — пропустить бэкап БД (НЕ рекомендуется)

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

# Тип БД определяем по .env (DJANGO_DATABASE=postgres|postgresql|pgsql →
# Postgres, иначе SQLite — как в creativesphere/settings.py).
ENV_FILE="$PROJECT_DIR/.env"
DB_KIND="sqlite"
if [ -f "$ENV_FILE" ] && grep -Eq '^DJANGO_DATABASE=(postgres|postgresql|pgsql)[[:space:]]*$' "$ENV_FILE"; then
    DB_KIND="postgres"
fi

log "=========================================="
log "Safe deploy: $PROJECT_DIR (db kind=$DB_KIND)"
log "=========================================="

# --- 1. Бэкап всей базы (Postgres: pg_dump; SQLite: копия файла) ---------
if [ "${SKIP_DB_BACKUP:-0}" != "1" ]; then
    if [ "$DB_KIND" = "postgres" ]; then
        DB_BACKUP="$BACKUP_DIR/db-$STAMP.dump"
        log "pg_dump ($POSTGRES_DB) -> $DB_BACKUP"
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
        SQLITE_PATH="$(grep -E '^DJANGO_SQLITE_PATH=' "$ENV_FILE" 2>/dev/null | head -n1 | cut -d= -f2- | tr -d '[:space:]')"
        [ -z "$SQLITE_PATH" ] && SQLITE_PATH="$PROJECT_DIR/db.sqlite3"
        if [ ! -f "$SQLITE_PATH" ]; then
            log "ОШИБКА: SQLite-файл не найден: $SQLITE_PATH — деплой прерван."
            log "(Если БД Postgres — задайте DJANGO_DATABASE=postgresql в .env;"
            log " чтобы пропустить бэкап осознанно — SKIP_DB_BACKUP=1.)"
            exit 1
        fi
        DB_BACKUP="$BACKUP_DIR/db-$STAMP.sqlite3"
        log "SQLite backup ($SQLITE_PATH) -> $DB_BACKUP"
        # sqlite3 .backup даёт консистентную копию даже при живых записях (WAL);
        # cp — запасной вариант, если CLI sqlite3 не установлен.
        if command -v sqlite3 >/dev/null 2>&1; then
            sqlite3 "$SQLITE_PATH" ".backup '$DB_BACKUP'"
        else
            cp -a "$SQLITE_PATH" "$DB_BACKUP"
        fi
        log "SQLite backup OK ($(du -h "$DB_BACKUP" | cut -f1))"
        # Оставляем только последние BACKUP_KEEP копий
        ls -1t "$BACKUP_DIR"/db-*.sqlite3 2>/dev/null \
            | tail -n +$((BACKUP_KEEP + 1)) \
            | xargs -r rm --
    fi
else
    log "SKIP_DB_BACKUP=1 — пропустил бэкап БД (НЕ РЕКОМЕНДУЕТСЯ)"
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
