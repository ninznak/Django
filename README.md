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

## Галерея портфолио «3D Барельефы и Медали»

Полный список работ на странице **`/portfolio/3d/`** формируется автоматически в модуле
**`core/portfolio_gallery_data.py`** (функция `portfolio_3d_gallery_items()`).

### Источник файлов

- Файлы подтягиваются из каталога **`static/images/news/`**.
- В галерею попадают все файлы, у которых в имени содержится `model`
  (напр. `model9.PNG`, `modelmid.JPEG`, `model000.JPEG`), файлы с маркером
  **`777`** в имени (напр. `georg777.jpg`, `efrosyn777.jpg`, `ushak777.jpg`),
  а также отдельно файл **`jimm.PNG`**. Дубликаты по расширению
  (`model6.JPG` + `model6.JPEG`) сохраняются оба.
- Чтобы добавить новую работу — достаточно положить файл в `static/images/news/`
  с `model` или `777` в имени. Пересобирать ничего не нужно.

### Порядок и приоритет

- Константа **`_PORTFOLIO_3D_TOP_ORDER`** задаёт явный порядок первых работ
  (по stem'у файла, в нижнем регистре). По умолчанию это:
  `model9 → model8 → model99 → efrosyn777 → georg777 → ushak777 →
  model4 → model00 → modelmid → model10 → jimm → model000`.
- Далее идёт курируемая «фиксированная» работа из списка
  **`_PORTFOLIO_3D_BASE`** (сейчас — «Барельеф здания в Москве», `zdanie.png`).
- После неё — остальные найденные файлы (`model*` и `*777*`) в алфавитном порядке.

Менять порядок top-работ можно прямо в `_PORTFOLIO_3D_TOP_ORDER`
(только stem-имена, без расширения).

### Исключения из галереи

- Константа **`_PORTFOLIO_3D_EXCLUDED`** — набор stem'ов, которые физически лежат
  в `news/`, но не должны появляться в галерее (и в превью-разделе `/portfolio/`).
- Текущие исключения: `model6`, `model11`.
- Чтобы скрыть работу — добавьте её stem в этот `frozenset`.
  Чтобы вернуть — уберите.

### Особые подписи (i18n)

Большинство карточек получают общий заголовок `portfolio_3d_model_piece`.
Словарь **`_PORTFOLIO_3D_CAPTIONS`** позволяет задать индивидуальные i18n-ключи:

- `model9` → `portfolio_model9_title` / `portfolio_model9_cat`
  («3D модель портрет (барельеф)»).
- `jimm` → `featured_jimm_title` / `featured_jimm_cat`
  («Трехмерная модель персонажа Червяк Джимм»).
- `efrosyn777` → `portfolio_efrosyn_title` / `portfolio_efrosyn_cat`
  («Святая Евфросиния Полоцкая»).
- `georg777` → `portfolio_georg_title` / `portfolio_georg_cat`
  («Святой Георгий Победоносец»).
- `ushak777` → `portfolio_ushak_title` / `portfolio_ushak_cat`
  («Святой праведный воин Феодор Ушаков»).

Сами тексты (RU/EN) хранятся в JS-словарях `translations.ru` / `translations.en`
внутри **`templates/core/base.html`**.

### Превью-раздел на `/portfolio/` (3 карточки)

Статичные превью в шаблоне **`templates/core/portfolio.html`** (блок `#portfolio-3d`)
задаются вручную: `news/model9.PNG`, `news/model5.jpg`, `news/model8.jpg`.
Клик по любой карточке открывает полную галерею `/portfolio/3d/`.

## Superuser Setup

```bash
python manage.py createsuperuser
```

Then access admin at `http://127.0.0.1:8000/admin/`  

