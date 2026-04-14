# CreativeSphere — Django site

Portfolio site built with **Django** (templates + static assets). No database beyond SQLite is required for the default setup.

## Local development

```bash
cd Django
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Production deploy (VPS)

See **[DEPLOY_VPS.md](./DEPLOY_VPS.md)** for full instructions and the automated script:

```bash
sudo bash scripts/deploy-vps.sh your-domain.com /path/to/project
```

### Автоматическое обновление с Git (cron, раз в сутки)

После того как сайт на VPS развёрнут как **git clone**, обновления кода делаются скриптом **`scripts/update.sh`** (pull → pip → migrate → collectstatic → restart Gunicorn).

Подробная инструкция: что настроить на сервере один раз, как повесить запуск на cron ночью, переменные `GIT_BRANCH` / `GUNICORN_SERVICE`, безопасность и чеклист — в **[scripts/AUTO_UPDATE.md](./scripts/AUTO_UPDATE.md)**. Пример строки для cron: **[scripts/crontab-daily.example](./scripts/crontab-daily.example)**.

Ручной запуск на сервере:

```bash
sudo bash /var/www/Django/scripts/update.sh /var/www/Django
```

## Configuration

- Copy **`.env.example`** to **`.env`** and set variables (especially `DJANGO_SECRET_KEY` and `ALLOWED_HOSTS` in production).  
- Static files: `python manage.py collectstatic` → `staticfiles/` (used behind Nginx).  

## Project layout

- `creativesphere/` — Django project settings  
- `core/` — views and URLs  
- `templates/core/` — HTML templates  
- `static/` — CSS, images

## Features

### Internet Store
- Session-based cart (no registration required)
- Checkout with full delivery address and contact information
- Order saved to database with email notification to admin
- Order tracking via Django Admin panel

### Admin Panel
Access at `/admin/` (requires superuser):
- View and manage orders with status tracking
- View order items and customer details
- Contact form submissions

### Personal Data Compliance (152-ФЗ)
- Explicit consent checkbox required for order submission
- Personal Data Policy published on `/copyright/#pd-policy`
- Consent recorded with timestamp and IP address
- Users can request data deletion via contact form

## Superuser Setup

```bash
python manage.py createsuperuser
```

Then access admin at `http://127.0.0.1:8000/admin/`  

