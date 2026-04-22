"""Единые правила доступа к управлению контентом.

Исторически одна и та же логика ("кто может публиковать", "кто может
зайти в профильную форму") жила в трёх местах:

* ``core/admin.py::_user_can_publish`` — используется в ``NewsArticleAdmin``
  и ``ProductAdmin`` для блокировки публикации у обычного staff.
* ``core/forms.py::_user_can_publish_content`` — та же проверка, чтобы
  ``ProductCreateForm`` / ``NewsArticleCreateForm`` не давали выставить
  ``is_published=True`` / ``status=published``.
* ``core/views.py::_user_is_content_manager`` / ``_user_can_publish_content_for_view``
  — для gating профильных вью ``/profile/products/add/`` и ``/profile/articles/add/``.

Держим их здесь, чтобы правила публикации задавались в одном месте, а
админка/формы/вью импортировали из общего модуля. ``role_key()`` нужен
отдельно — он отдаёт ключ i18n для рендера роли в шаблоне ``profile.html``
(см. AGENTS.md §7 «Translations»).
"""
from __future__ import annotations

from functools import wraps
from typing import Callable

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


# Имя группы, которой разрешена публикация контента.
# Если нужно — переименуйте здесь, и во всех трёх call-sites обновится
# автоматически (см. docstring модуля).
EDITORS_GROUP_NAME = "Editors"


def can_publish_content(user) -> bool:
    """Может ли пользователь публиковать статьи/товары сразу.

    Правило: superuser **или** участник группы ``EDITORS_GROUP_NAME``.
    Обычный staff этим правом НЕ обладает (может только черновик).
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=EDITORS_GROUP_NAME).exists()


def can_manage_content(user) -> bool:
    """Может ли пользователь открывать профильные формы добавления контента.

    Правило: superuser, staff или Editors. Т.е. *шире*, чем
    ``can_publish_content`` — обычный staff заходит в форму, но сможет
    сохранить только как черновик (публикацию блокирует форма/админка).
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name=EDITORS_GROUP_NAME).exists()


def role_key(user) -> str:
    """Короткий ключ роли для i18n (``profile_role_<key>`` в ``base.html``).

    Значения: ``admin``, ``editor``, ``staff``, ``user``, ``guest``.
    """
    if not user or not user.is_authenticated:
        return "guest"
    if user.is_superuser:
        return "admin"
    if user.groups.filter(name=EDITORS_GROUP_NAME).exists():
        return "editor"
    if user.is_staff:
        return "staff"
    return "user"


# Русские подписи ролей для SSR-первого рендера страницы профиля
# (JS затем может перерисовать по ``data-i18="profile_role_{{ key }}"``).
_ROLE_LABELS_RU: dict[str, str] = {
    "admin": "Администратор",
    "editor": "Редактор",
    "staff": "Сотрудник",
    "user": "Пользователь",
    "guest": "Гость",
}


def role_label_ru(user) -> str:
    """Русская метка роли для первичного рендера ``profile.html``."""
    return _ROLE_LABELS_RU[role_key(user)]


def require_content_manager(view_func: Callable) -> Callable:
    """Декоратор: пускает только ``can_manage_content`` пользователей.

    * Неаутентифицированных редиректит на ``core:sign_up_login`` с ``?next=``.
    * Аутентифицированных, но не подходящих по правам, отправляет в
      ``core:profile`` с flash-сообщением.

    Чтобы не ломать существующие тесты авторизации, сообщения берутся из
    той же строковой базы, что раньше использовалась в ``views.py``.
    """

    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect(f"{reverse('core:sign_up_login')}?next={request.path}")
        if not can_manage_content(request.user):
            messages.error(
                request,
                "Добавлять контент могут только сотрудники и редакторы.",
            )
            return redirect("core:profile")
        return view_func(request, *args, **kwargs)

    return _wrapped
