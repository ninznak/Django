# Автоматическое обновление сайта с Git на VPS (раз в сутки)

В проекте уже есть скрипт **`update.sh`**: он подтягивает код из Git, обновляет зависимости, применяет миграции, собирает статику и перезапускает Gunicorn. Ниже — как включить запуск **по расписанию** (например, ночью) и что нужно сделать один раз на сервере.

---

## Что делает `scripts/update.sh`

Кратко, по шагам:

1. Переходит в каталог проекта (по умолчанию `/var/www/Django`, либо путь из первого аргумента).
2. При необходимости добавляет репозиторий в `git config --global safe.directory` (чтобы `git pull` от root не ругался на «dubious ownership», если каталог принадлежит `www-data`).
3. Выполняет **`git pull origin <ветка>`** (ветка задаётся переменной окружения **`GIT_BRANCH`**, по умолчанию **`main`**).
4. Выставляет **`chown -R www-data:www-data`** на весь каталог проекта.
5. От имени **`www-data`**: активация venv → **`pip install -r requirements.txt`** → **`migrate --noinput`** → **`collectstatic --noinput`**.
6. Перезапускает systemd-службу Gunicorn (имя по умолчанию **`creativesphere-gunicorn`**, можно переопределить **`GUNICORN_SERVICE`**).

Лог пишется в **`deploy/update.log`** внутри корня проекта (каталог `deploy/` создаётся автоматически).

Запуск вручную (как в [DEPLOY_VPS.md](../DEPLOY_VPS.md)):

```bash
sudo bash /var/www/Django/scripts/update.sh
# или с явным путём:
sudo bash /path/to/Django/scripts/update.sh /path/to/Django
```

Другая ветка (если не `main`):

```bash
sudo env GIT_BRANCH=master bash /var/www/Django/scripts/update.sh
```

Другая служба Gunicorn (если переименовали unit):

```bash
sudo env GUNICORN_SERVICE=my-gunicorn bash /var/www/Django/scripts/update.sh
```

---

## Что нужно для «окончательной» схемы автообновления

### 1. Проект на VPS — это клон Git

На сервере в каталоге деплоя должен быть **репозиторий** (`git status` показывает ветку), а не только залитые по SFTP файлы. Иначе `git pull` нечего будет обновлять.

- Один раз: `git clone <url> /var/www/Django` (или скопировать и `git init` + remote — хуже для продакшена).
- Remote должен указывать на тот же репозиторий, куда вы пушите с рабочей машины.

### 2. Доступ Git с сервера к remote

Выберите один вариант:

- **HTTPS + токен** (GitHub/GitLab Personal Access Token в URL или в credential helper) — проще, но токен нужно хранить аккуратно.
- **SSH deploy key** — ключ только на чтение, добавленный в Deploy keys репозитория; на сервере `~/.ssh` для пользователя, от которого выполняется `git pull` (см. ниже про cron).

Если `sudo bash update.sh` выполняется от root, `git pull` идёт от root — у root должен быть настроен доступ к Git (или используйте общий системный credential).

### 3. Ветка по умолчанию совпадает с продом

На сервере: `git branch` и на GitHub — какая ветка «дефолтная». Если прод — не `main`, на сервере и в cron задайте:

```bash
export GIT_BRANCH=master   # пример
```

### 4. Один раз проверить ручной запуск

```bash
sudo bash /var/www/Django/scripts/update.sh /var/www/Django
```

Убедитесь, что в конце **`deploy/update.log`** нет ошибок, а сайт открывается. Проверка службы:

```bash
sudo systemctl status creativesphere-gunicorn
```

### 5. Настроить cron (или systemd timer)

**Пример: каждый день в 03:15** (мало трафика; время подстройте под часовой пояс сервера):

```cron
15 3 * * * root /bin/bash /var/www/Django/scripts/update.sh /var/www/Django >> /var/www/Django/deploy/cron.log 2>&1
```

- Путь к скрипту и к проекту замените на ваши реальные.
- Дублирование логов: основной лог — `deploy/update.sh` внутри скрипта; `cron.log` — оболочка cron (удобно видеть, что cron вообще отработал).

Установка: `sudo crontab -e` для пользователя **root** **или** файл `/etc/cron.d/creativesphere-update`:

```
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

15 3 * * * root /bin/bash /var/www/Django/scripts/update.sh /var/www/Django >> /var/www/Django/deploy/cron.log 2>&1
```

После правки системного cron обычно не нужен `reload`, но проверьте синтаксис.

**Альтернатива:** `systemd.timer` — если не хотите cron; логика та же: вызов того же `update.sh`.

### 6. Переменные для ночного cron

Если ветка не `main`, в crontab можно так:

```cron
15 3 * * * root GIT_BRANCH=main GUNICORN_SERVICE=creativesphere-gunicorn /bin/bash /var/www/Django/scripts/update.sh /var/www/Django >> /var/www/Django/deploy/cron.log 2>&1
```

(В одной строке cron переменные задаются перед командой.)

### 7. Что не трогает скрипт (важно помнить)

- **`.env`** на сервере не перезаписывается скриптом обновления (он в `.gitignore`). После смены переменных в коде проверьте `.env` вручную.
- **Nginx / SSL** — скрипт не перезагружает Nginx. Меняйте конфиги отдельно: `sudo nginx -t && sudo systemctl reload nginx`.
- **Бэкап БД** — для SQLite можно добавить отдельный cron с копией `db.sqlite3`; для PostgreSQL — `pg_dump`. Это не входит в `update.sh`.

### 8. Безопасность и откат

- Автообновление подтягивает **любой** новый коммит в выбранной ветке. Имеет смысл защитить `main` в Git (review, CI) перед merge.
- При ошибке миграции скрипт завершится с ненулевым кодом; Gunicorn мог перезапуститься после успешных шагов — смотрите `deploy/update.log` и `journalctl -u creativesphere-gunicorn`.

---

## Файлы в репозитории

| Файл | Назначение |
|------|------------|
| `scripts/update.sh` | Основной сценарий обновления (ручной и из cron) |
| `scripts/crontab-daily.example` | Пример строки для cron |
| `scripts/AUTO_UPDATE.md` | Эта инструкция |
| [DEPLOY_VPS.md](../DEPLOY_VPS.md) | Первичный деплой VPS и ссылка на `update.sh` |

---

## Краткий чеклист перед включением nightly

- [ ] На VPS — git clone, `git pull` вручную работает.
- [ ] `sudo bash scripts/update.sh` проходит без ошибок.
- [ ] Ветка `GIT_BRANCH` совпадает с продом.
- [ ] Доступ к remote с сервера настроен (SSH или HTTPS+token).
- [ ] В cron указан верный путь к проекту и к `update.sh`.
- [ ] По желанию: ротация или мониторинг `deploy/update.log` / `deploy/cron.log`.
