# Откат глитча на заголовке hero («Встречает интеллект»)

## Быстро (без удаления файлов)

В `.env` локально или на сервере:

```env
HERO_TITLE_GLITCH_ENABLED=0
```

Перезапустите Gunicorn (`sudo systemctl restart creativesphere-gunicorn`) или dev-сервер.

Вернётся прежний `.text-gradient-animated` с shimmer из `base.html`.

## Полное удаление фичи

1. Удалить:
   - `static/css/hero-title-glitch.css`
   - `static/js/hero-title-glitch.js`
   - этот файл
2. В `templates/core/homepage.html` убрать `{% if hero_title_glitch_enabled %}` вокруг заголовка, оставить только `text-gradient-animated`.
3. Убрать подключение CSS/JS глитча из `homepage.html`.
4. Удалить `HERO_TITLE_GLITCH_ENABLED` из `creativesphere/settings.py`, `hero_title_glitch_enabled` из `core/context_processors.py`.
5. Убрать вызов `syncHeroTitleGlitch()` из `templates/core/base.html` (`updatePageTranslations`).
6. Удалить `HeroTitleGlitchTests` из `core/tests.py`.
