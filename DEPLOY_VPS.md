# Deploy CreativeSphere (Django) to a VPS

This guide targets **Ubuntu 22.04/24.04** (or Debian 12) with **Nginx**, **Gunicorn** under **systemd**, **Let’s Encrypt** SSL, and a **Python virtualenv**.

## What you need

- A VPS with a public IP and SSH access  
- **DNS** **A** records for every hostname you use: `trally.ru`, `www.trally.ru`, `kurilenkoart.ru`, `www.kurilenkoart.ru` (when using both) → VPS IP  
- The project uploaded to the server (e.g. `/var/www/Django`)

## Quick path: automated script

From the **Django project root** on the server (the folder that contains `manage.py`):

```bash
sudo bash scripts/deploy-vps.sh trally.ru /var/www/Django
```

This uses **trally.ru** as the **canonical** URL (`PUBLIC_SITE_URL`, SEO) and automatically adds **kurilenkoart.ru** to Nginx, Certbot, and `DJANGO_SITE_DOMAINS` on the same VPS.

- Only **trally.ru**: `sudo env DEPLOY_SINGLE_DOMAIN=1 bash scripts/deploy-vps.sh trally.ru /var/www/Django`  
- **kurilenkoart.ru** as primary with **trally.ru** alias: `sudo bash scripts/deploy-vps.sh kurilenkoart.ru /var/www/Django trally.ru`  

Optional: set the email Let’s Encrypt uses for expiry notices:

```bash
export LETSENCRYPT_EMAIL=you@example.com
sudo -E bash scripts/deploy-vps.sh trally.ru /var/www/Django
```

The script will:

1. Install **Python 3**, **venv**, **Nginx**, **Certbot** (no Node.js)  
2. Create `venv/`, `pip install -r requirements.txt`  
3. Write `.env` with `DEBUG=0`, `DJANGO_SITE_DOMAINS`, `DJANGO_CANONICAL_DOMAIN`, `PUBLIC_SITE_URL`, and a random `DJANGO_SECRET_KEY` (Django derives `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`)  
4. `chown` the app tree to **www-data** and run `migrate` / `collectstatic` as **www-data**  
5. Install **systemd** unit `creativesphere-gunicorn` → Gunicorn on `127.0.0.1:8000`  
6. Configure **Nginx** `server_name` for all apices + `www`, proxy headers for HTTPS  
7. Run **certbot** for every name and enable HTTP→HTTPS redirect  

After deploy:

- **Canonical** site for SEO: `https://trally.ru` (or whichever domain you passed first)  
- **Also works**: `https://kurilenkoart.ru` when included in `DJANGO_SITE_DOMAINS`  
- Logs: `sudo journalctl -u creativesphere-gunicorn -f`  
- Restart: `sudo systemctl restart creativesphere-gunicorn`  

### Switching the canonical domain to kurilenkoart.ru later

On the server, edit `.env`: set `DJANGO_CANONICAL_DOMAIN=kurilenkoart.ru` and `PUBLIC_SITE_URL=https://kurilenkoart.ru`, keep `DJANGO_SITE_DOMAINS=trally.ru,kurilenkoart.ru` if both should still work, then `sudo systemctl restart creativesphere-gunicorn`. Add **301 redirects** in Nginx if you want all traffic on one hostname only.  

### Updating the site after code changes

**Automated (recommended if the server is a Git clone):**

```bash
sudo bash /var/www/Django/scripts/update.sh
# or another app root:
sudo bash /path/to/Django/scripts/update.sh /path/to/Django
```

This runs: `git pull origin main` (or the branch in **`GIT_BRANCH`**) → adds **`git config --global safe.directory`** for the app path if missing (avoids “dubious ownership” when root pulls a **www-data**-owned repo) → `chown www-data` → `pip install` → `migrate` → `collectstatic` → `systemctl restart creativesphere-gunicorn`. Logs append to **`deploy/update.log`** under the project root (writable without touching `/var/log`).

**Before the first update on a new server:** ensure the remote and default branch match (`git remote -v`, `git branch -a`). If your default branch is not `main`, run e.g. `sudo env GIT_BRANCH=master bash /var/www/Django/scripts/update.sh`. Confirm `creativesphere-gunicorn` exists (`systemctl list-units 'creativesphere*'`).

**Without Git (SFTP / zip):** upload changed files into `/var/www/Django`, then run only:

```bash
sudo chown -R www-data:www-data /var/www/Django
sudo -u www-data bash -c 'cd /var/www/Django && source venv/bin/activate && pip install -r requirements.txt && python manage.py migrate --noinput && python manage.py collectstatic --noinput'
sudo systemctl restart creativesphere-gunicorn
```

**Nginx:** reload only if you changed site config (`sudo nginx -t && sudo systemctl reload nginx`). **Do not overwrite** production `.env` when uploading.

**From your PC (push then pull on VPS):** commit and push to your remote, SSH to the VPS, then run `sudo bash .../scripts/update.sh`.

## Manual deployment (overview)

If you prefer not to use the script:

1. **Install**: `python3-venv`, `nginx`, `certbot`, `python3-certbot-nginx`  
2. **Clone/copy** project to e.g. `/var/www/Django`  
3. **venv**: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`  
4. **`.env`**: copy from `.env.example`; set `DJANGO_SECRET_KEY`, `DEBUG=0`, `DJANGO_SITE_DOMAINS`, `DJANGO_CANONICAL_DOMAIN`, `PUBLIC_SITE_URL`  
5. **Django**: `python manage.py migrate --noinput` and `python manage.py collectstatic --noinput`  
6. **Gunicorn**: bind `127.0.0.1:8000` — see `deploy/creativesphere-gunicorn.service`  
7. **Nginx**: `server_name` all hosts; `location /static/` → `staticfiles/`, `location /media/` → `media/`, `location /` → proxy to Gunicorn  
8. **SSL**: `certbot --nginx` with `-d` for each apex and `www` (e.g. four names per domain)  

## Security notes

- Keep `.env` out of Git; use strong `DJANGO_SECRET_KEY` in production.  
- Restrict hosts via `DJANGO_SITE_DOMAINS` (or explicit `ALLOWED_HOSTS` in `.env`).  
- For SQLite, ensure the process user can read/write `db.sqlite3` if you change the user from `root`.  
- Consider PostgreSQL/MySQL for production traffic; SQLite is fine for small sites.  

## Troubleshooting

| Issue | What to check |
|--------|----------------|
| 502 Bad Gateway | `systemctl status creativesphere-gunicorn`, `journalctl -u creativesphere-gunicorn -n 50` |
| Static files 404 | `collectstatic` ran; Nginx `alias` path matches `STATIC_ROOT` |
| CSRF / login issues | Each `https://apex` and `https://www.apex` is derived from `DJANGO_SITE_DOMAINS`, or set `CSRF_TRUSTED_ORIGINS` manually |
| Certbot fails | DNS A records point to this server; ports 80/443 open |

## Files for deployment

- `scripts/deploy-vps.sh` — one-shot installer  
- `deploy/creativesphere-gunicorn.service` — reference unit file (script writes `/etc/systemd/system/creativesphere-gunicorn.service`)  
- `.env.example` — template for environment variables  
- `requirements.txt` — includes `gunicorn` and `python-dotenv`  
