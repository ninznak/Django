# Deploy CreativeSphere (Django) to a VPS

This guide targets **Ubuntu 22.04/24.04** (or Debian 12) with **Nginx**, **Gunicorn** under **systemd**, **Let's Encrypt** SSL, and a **Python virtualenv**.

## What you need

- A VPS with a public IP and SSH access
- **DNS** **A** records for the hostnames you serve — by default `kurilenkoart.ru` and `www.kurilenkoart.ru` → VPS IP
- Open inbound ports **80** and **443** on the firewall
- The project uploaded to the server (e.g. `/var/www/Django`)

## Quick path: automated script

From the **Django project root** on the server (the folder that contains `manage.py`):

```bash
sudo bash scripts/deploy-vps.sh
```

With no arguments the script uses `kurilenkoart.ru` as the **canonical** domain (`PUBLIC_SITE_URL`, SEO) and `/var/www/Django` as the app directory. Equivalent explicit form:

```bash
sudo bash scripts/deploy-vps.sh kurilenkoart.ru /var/www/Django
```

Need extra apices served alongside the canonical one? Pass them as additional arguments — Nginx `server_name` and the certbot certificate will cover every apex plus its `www` sub-host:

```bash
sudo bash scripts/deploy-vps.sh kurilenkoart.ru /var/www/Django another-apex.ru
```

Set the email Let's Encrypt uses for expiry notices (optional but recommended):

```bash
export LETSENCRYPT_EMAIL=you@example.com
sudo -E bash scripts/deploy-vps.sh
```

The script will:

1. Install **Python 3**, **venv**, **Nginx**, **Certbot** + the Nginx plugin
2. Create `venv/`, `pip install -r requirements.txt`
3. Write `.env` with `DEBUG=0`, `DJANGO_SITE_DOMAINS`, `DJANGO_CANONICAL_DOMAIN`, `PUBLIC_SITE_URL`, and a random `DJANGO_SECRET_KEY` (Django derives `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`)
4. `chown` the app tree to **www-data** and run `migrate` / `collectstatic` as **www-data**
5. Install **systemd** unit `creativesphere-gunicorn` → Gunicorn on `127.0.0.1:8000`
6. Configure **Nginx** `server_name` for every apex + `www`, set proxy headers so Django sees HTTPS
7. Run **`certbot --nginx -d kurilenkoart.ru -d www.kurilenkoart.ru --redirect`** — issues the Let's Encrypt certificate and rewrites the Nginx config with a **301 HTTP→HTTPS redirect**

## SSL certificate — how it is obtained and renewed

- Issuance: a single Let's Encrypt certificate covering every `<apex>` and `www.<apex>` passed to the script. DNS for every name must already point at the VPS, otherwise the HTTP-01 challenge fails and certbot exits with an error — the script stops and prints the exact command to retry.
- Redirect: `certbot --nginx --redirect` adds a `return 301 https://$host$request_uri;` server block on :80 so every HTTP request upgrades to HTTPS.
- Auto-renewal: the `certbot` Debian/Ubuntu package installs `certbot.timer` (systemd) that runs twice daily and renews any certificate in its last 30 days. Verify once with:

  ```bash
  systemctl list-timers 'certbot*'
  sudo certbot renew --dry-run
  ```

- Manual renew / re-issue with a new hostname later:

  ```bash
  sudo certbot --nginx -d kurilenkoart.ru -d www.kurilenkoart.ru --redirect
  ```

After deploy you should have:

- **Canonical** site for SEO: `https://kurilenkoart.ru`
- `https://www.kurilenkoart.ru` also works (certificate covers it; Nginx serves the same app)
- Logs: `sudo journalctl -u creativesphere-gunicorn -f`
- Restart: `sudo systemctl restart creativesphere-gunicorn`

### Updating the site after code changes

**Automated (recommended if the server is a Git clone):**

```bash
sudo bash /var/www/Django/scripts/update.sh
# or another app root:
sudo bash /path/to/Django/scripts/update.sh /path/to/Django
```

This runs: `git pull origin main` (or the branch in **`GIT_BRANCH`**) → adds **`git config --global safe.directory`** for the app path if missing (avoids "dubious ownership" when root pulls a **www-data**-owned repo) → `chown www-data` → `pip install` → `migrate` → `collectstatic` → `systemctl restart creativesphere-gunicorn`. Logs append to **`deploy/update.log`** under the project root (writable without touching `/var/log`).

**Before the first update on a new server:** ensure the remote and default branch match (`git remote -v`, `git branch -a`). If your default branch is not `main`, run e.g. `sudo env GIT_BRANCH=master bash /var/www/Django/scripts/update.sh`. Confirm `creativesphere-gunicorn` exists (`systemctl list-units 'creativesphere*'`).

**Without Git (SFTP / zip):** upload changed files into `/var/www/Django`, then run only:

```bash
sudo chown -R www-data:www-data /var/www/Django
sudo -u www-data bash -c 'cd /var/www/Django && source venv/bin/activate && pip install -r requirements.txt && python manage.py migrate --noinput && python manage.py collectstatic --noinput'
sudo systemctl restart creativesphere-gunicorn
```

**Nginx:** reload only if you changed site config (`sudo nginx -t && sudo systemctl reload nginx`). **Do not overwrite** production `.env` when uploading.

**From your PC (push then pull on VPS):** commit and push to your remote, SSH to the VPS, then run `sudo bash .../scripts/update.sh`.

**Nightly / scheduled updates (cron):** see **[scripts/AUTO_UPDATE.md](./scripts/AUTO_UPDATE.md)** for prerequisites (Git access from the server, branch name, one-time manual test) and a crontab example in **`scripts/crontab-daily.example`**.

## Manual deployment (overview)

If you prefer not to use the script:

1. **Install**: `python3-venv`, `nginx`, `certbot`, `python3-certbot-nginx`
2. **Clone/copy** project to e.g. `/var/www/Django`
3. **venv**: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
4. **`.env`**: copy from `.env.example`; set `DJANGO_SECRET_KEY`, `DEBUG=0`, `DJANGO_SITE_DOMAINS=kurilenkoart.ru`, `DJANGO_CANONICAL_DOMAIN=kurilenkoart.ru`, `PUBLIC_SITE_URL=https://kurilenkoart.ru`
5. **Django**: `python manage.py migrate --noinput` and `python manage.py collectstatic --noinput`
6. **Gunicorn**: bind `127.0.0.1:8000` — see `deploy/creativesphere-gunicorn.service`
7. **Nginx**: `server_name kurilenkoart.ru www.kurilenkoart.ru;` → `location /static/` → `staticfiles/`, `location /media/` → `media/`, `location /` → proxy to Gunicorn
8. **SSL**: `sudo certbot --nginx -d kurilenkoart.ru -d www.kurilenkoart.ru --redirect`

## Security notes

- Keep `.env` out of Git; use a strong `DJANGO_SECRET_KEY` in production.
- Restrict hosts via `DJANGO_SITE_DOMAINS` (or explicit `ALLOWED_HOSTS` in `.env`).
- For SQLite, ensure the process user can read/write `db.sqlite3` if you change the user from `root`.
- Consider PostgreSQL/MySQL for production traffic; SQLite is fine for small sites.

## Troubleshooting

| Issue | What to check |
|--------|----------------|
| 502 Bad Gateway | `systemctl status creativesphere-gunicorn`, `journalctl -u creativesphere-gunicorn -n 50` |
| Static files 404 | `collectstatic` ran; Nginx `alias` path matches `STATIC_ROOT` |
| CSRF / login issues | Each `https://apex` and `https://www.apex` is derived from `DJANGO_SITE_DOMAINS`, or set `CSRF_TRUSTED_ORIGINS` manually |
| Certbot fails | DNS A records for `kurilenkoart.ru` and `www.kurilenkoart.ru` point to this server; ports 80/443 open; no firewall between Let's Encrypt and the VPS |
| Cert not renewing | `systemctl status certbot.timer`; `sudo certbot renew --dry-run` |

## Files for deployment

- `scripts/deploy-vps.sh` — one-shot installer (defaults to `kurilenkoart.ru`)
- `scripts/update.sh` — pull + migrate + collectstatic + restart Gunicorn (manual or cron)
- `scripts/AUTO_UPDATE.md` — how to enable daily Git updates on the VPS (cron, checklist)
- `scripts/crontab-daily.example` — example cron entry
- `deploy/creativesphere-gunicorn.service` — reference unit file (script writes `/etc/systemd/system/creativesphere-gunicorn.service`)
- `.env.example` — template for environment variables
- `requirements.txt` — includes `gunicorn` and `python-dotenv`
