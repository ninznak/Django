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

## Configuration

- Copy **`.env.example`** to **`.env`** and set variables (especially `DJANGO_SECRET_KEY` and `ALLOWED_HOSTS` in production).  
- Static files: `python manage.py collectstatic` → `staticfiles/` (used behind Nginx).  

## Project layout

- `creativesphere/` — Django project settings  
- `core/` — views and URLs  
- `templates/core/` — HTML templates  
- `static/` — CSS, images  
