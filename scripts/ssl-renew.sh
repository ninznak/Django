#!/usr/bin/env bash
# ssl-renew.sh — продление Let's Encrypt сертификатов + reload Nginx.
#
# certbot renew сам решает, что продлевать: трогает только сертификаты,
# у которых осталось < 30 дней. Скрипт безопасно запускать хоть каждый день —
# если продлевать нечего, он просто запишет в лог даты истечения и выйдет.
#
# Обычно на Ubuntu/Debian продлением уже занимается системный certbot.timer
# (ставится пакетом certbot). Этот скрипт — страховка и ручной инструмент:
#   * если timer отключён/сломан, cron с этим скриптом всё равно продлит;
#   * удобно запускать руками и видеть сроки сертификатов в одном месте.
#
# Usage:
#   sudo bash scripts/ssl-renew.sh              # обычный запуск
#   sudo bash scripts/ssl-renew.sh --dry-run    # репетиция без реального продления
#   sudo bash scripts/ssl-renew.sh /var/www/Django --dry-run
#
# Cron (страховка раз в неделю, понедельник 04:20; certbot.timer не мешает):
#   20 4 * * 1 root /bin/bash /var/www/Django/scripts/ssl-renew.sh /var/www/Django >> /var/www/Django/deploy/cron.log 2>&1

set -euo pipefail

PROJECT_DIR="/var/www/Django"
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *)         PROJECT_DIR="$arg" ;;
  esac
done

LOG_DIR="$PROJECT_DIR/deploy"
LOG_FILE="$LOG_DIR/ssl-renew.log"
mkdir -p "$LOG_DIR"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE"
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "Запустите с sudo/root: certbot и reload nginx требуют прав root."
  exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
  log "ОШИБКА: certbot не установлен. Установка: apt-get install -y certbot python3-certbot-nginx"
  exit 1
fi

log "=========================================="
log "SSL renew check (dry-run=$DRY_RUN)"
log "=========================================="

# Текущие сертификаты и сроки — в лог (удобно смотреть историю).
certbot certificates 2>/dev/null | grep -E "Certificate Name|Domains|Expiry Date" \
    | sed 's/^[[:space:]]*//' | while IFS= read -r line; do
    log "  $line"
done

RENEW_ARGS=( renew --non-interactive )
# Nginx перезагружаем ТОЛЬКО если какой-то сертификат реально продлился.
RENEW_ARGS+=( --deploy-hook "systemctl reload nginx" )
if [[ "$DRY_RUN" -eq 1 ]]; then
  RENEW_ARGS+=( --dry-run )
fi

log "certbot ${RENEW_ARGS[*]}"
if certbot "${RENEW_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"; then
  log "certbot renew завершён успешно"
else
  RC=$?
  log "ОШИБКА: certbot renew упал с кодом $RC"
  log "Диагностика: certbot certificates; journalctl -u nginx; nginx -t"
  log "Частые причины: DNS больше не указывает на этот VPS; порт 80 закрыт;"
  log "конфиг Nginx сломан (certbot --nginx не может пройти HTTP-челлендж)."
  exit $RC
fi

# Подстраховка: убедиться, что системный таймер продления вообще включён.
if systemctl is-enabled certbot.timer >/dev/null 2>&1; then
  log "certbot.timer: включён (системное авто-продление работает)"
else
  log "ВНИМАНИЕ: certbot.timer не включён. Включить: systemctl enable --now certbot.timer"
  log "Пока timer выключен, продление держится только на cron с этим скриптом."
fi

log "Готово. Лог: $LOG_FILE"
