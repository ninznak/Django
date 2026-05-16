# Откат мобильной hero-карусели (стопка + тап)

## Быстро (без правки кода)

В `.env` на сервере или локально:

```env
HERO_MOBILE_STACK_ENABLED=0
```

Перезапустите Gunicorn (`sudo systemctl restart creativesphere-gunicorn`).

Поведение вернётся к прежнему: карусель `.cs-deck` с `hidden md:flex` (с md), на телефонах превью в hero не показывается.

## Полное удаление фичи

1. Удалить файлы:
   - `static/css/hero-mobile-deck.css`
   - `static/js/hero-mobile-deck.js`
   - `templates/core/includes/hero_carousel_cards.html`
2. В `templates/core/homepage.html` удалить блоки между `HERO_MOBILE_STACK_START` и `HERO_MOBILE_STACK_END`, вернуть inline-разметку трёх карточек в `.cs-deck`.
3. Убрать `{% block extra_css %}` / скрипт `hero-mobile-deck.js` из `homepage.html`.
4. Удалить `HERO_MOBILE_STACK_ENABLED` из `creativesphere/settings.py` и `hero_mobile_stack_enabled` из `core/context_processors.py`.
