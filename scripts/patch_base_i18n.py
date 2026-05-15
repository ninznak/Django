"""Replace inline translations in base.html with JSON fetch loader."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "templates" / "core" / "base.html"
I18N = ROOT / "static" / "js" / "i18n"

NEW_KEYS = {
    "ru": {
        "auth_invite_only": "Регистрация по приглашению. Обратитесь к администратору сайта.",
        "auth_forgot_link": "Забыли пароль?",
        "cart_added_toast": "Товар добавлен в корзину",
        "shop_hide_sold": "Скрыть распроданное",
        "shop_search_placeholder": "Поиск по названию…",
        "shop_search_label": "Поиск в магазине",
        "free_download_zip": "Скачать ZIP",
        "footer_contact_form": "Быстрая форма",
        "form_contact_name": "Имя",
        "form_contact_email": "Email",
        "form_contact_subject": "Тема",
        "form_contact_message": "Сообщение",
        "form_contact_send": "Отправить",
        "checkout_name": "Ваше имя",
        "checkout_email": "Email для связи",
        "checkout_phone": "Телефон (необязательно)",
        "checkout_country": "Страна",
        "checkout_city": "Город",
        "checkout_address": "Адрес (необязательно)",
        "checkout_postal": "Почтовый индекс",
        "checkout_notes": "Комментарий к заказу",
        "checkout_summary": "Ваш заказ",
        "order_next_steps": "Что дальше?",
        "order_email_copy": "Копия заказа отправлена на ваш email.",
        "profile_change_password": "Сменить пароль",
        "profile_site_settings": "Настройки главной",
        "busy_modal_title": "Загруженность автора",
        "breadcrumb_home": "Главная",
    },
    "en": {
        "auth_invite_only": "Registration is by invitation only. Please contact the site administrator.",
        "auth_forgot_link": "Forgot password?",
        "cart_added_toast": "Added to cart",
        "shop_hide_sold": "Hide sold out",
        "shop_search_placeholder": "Search by title…",
        "shop_search_label": "Search shop",
        "free_download_zip": "Download ZIP",
        "footer_contact_form": "Quick message",
        "form_contact_name": "Name",
        "form_contact_email": "Email",
        "form_contact_subject": "Subject",
        "form_contact_message": "Message",
        "form_contact_send": "Send",
        "checkout_name": "Your name",
        "checkout_email": "Contact email",
        "checkout_phone": "Phone (optional)",
        "checkout_country": "Country",
        "checkout_city": "City",
        "checkout_address": "Address (optional)",
        "checkout_postal": "Postal code",
        "checkout_notes": "Order notes",
        "checkout_summary": "Your order",
        "order_next_steps": "What happens next?",
        "order_email_copy": "A copy of your order was sent to your email.",
        "profile_change_password": "Change password",
        "profile_site_settings": "Homepage settings",
        "busy_modal_title": "Author availability",
        "breadcrumb_home": "Home",
    },
}


def main() -> None:
    text = BASE.read_text(encoding="utf-8")
    start = text.index("        // Language data - translations")
    end = text.index("        let currentLang = ")
    replacement = """        // Language data — static/js/i18n/*.json
        let translations = { ru: {}, en: {} };
        const I18N_STATIC_BASE = "{% static 'js/i18n/' %}";
        let i18nReady = null;
        function loadTranslations() {
            if (!i18nReady) {
                i18nReady = Promise.all([
                    fetch(I18N_STATIC_BASE + "ru.json").then(function (r) { return r.json(); }),
                    fetch(I18N_STATIC_BASE + "en.json").then(function (r) { return r.json(); }),
                ]).then(function (pair) {
                    translations = { ru: pair[0], en: pair[1] };
                });
            }
            return i18nReady;
        }

"""
    text = text[:start] + replacement + text[end:]

    old_dom = """document.addEventListener('DOMContentLoaded', function() {
            setupThemeToggle();
            setupMobileNav();
            const savedLang = localStorage.getItem('lang') || 'ru';
            setLang(savedLang);
        });"""
    new_dom = """document.addEventListener('DOMContentLoaded', function() {
            setupThemeToggle();
            setupMobileNav();
            const savedLang = localStorage.getItem('lang') || 'ru';
            loadTranslations().then(function () { setLang(savedLang); }).catch(function () { setLang(savedLang); });
        });"""
    if old_dom not in text:
        raise SystemExit("DOMContentLoaded block not found")
    text = text.replace(old_dom, new_dom, 1)

    needle = "            document.querySelectorAll('[data-i18-aria-label]').forEach(el => {"
    label_block = """            document.querySelectorAll('[data-i18-label]').forEach(el => {
                const key = el.getAttribute('data-i18-label');
                if (key && t[key]) el.textContent = t[key];
            });

"""
    if needle not in text:
        raise SystemExit("aria-label block not found")
    text = text.replace(needle, label_block + needle, 1)

    BASE.write_text(text, encoding="utf-8")

    for lang in ("ru", "en"):
        path = I18N / f"{lang}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(NEW_KEYS[lang])
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Patched base.html; merged", len(NEW_KEYS["ru"]), "new keys per locale")


if __name__ == "__main__":
    main()
