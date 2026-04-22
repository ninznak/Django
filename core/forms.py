from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import NewsArticle, Product
from .permissions import can_publish_content

User = get_user_model()


# Единый набор атрибутов для текстовых инпутов в "пользовательской" форме
# добавления контента (стиль совпадает с CheckoutForm).
_CONTENT_INPUT_CLASS = (
    "w-full px-4 py-2.5 border border-gray-200 rounded-xl bg-white "
    "focus:ring-2 focus:ring-[#3d7a4f] focus:border-transparent outline-none"
)
_CONTENT_TEXTAREA_CLASS = _CONTENT_INPUT_CLASS
_CONTENT_SELECT_CLASS = _CONTENT_INPUT_CLASS
_CONTENT_CHECKBOX_CLASS = (
    "w-4 h-4 text-[#3d7a4f] border-gray-300 rounded focus:ring-[#3d7a4f]"
)


class ContactForm(forms.Form):
    name = forms.CharField(max_length=120, required=True)
    email = forms.EmailField(required=True)
    subject = forms.CharField(max_length=200, required=True)
    message = forms.CharField(
        required=True,
        max_length=5000,
        widget=forms.Textarea(attrs={"rows": 5}),
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (*UserCreationForm.Meta.fields, "email")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already registered.")
        return email


class CheckoutForm(forms.Form):
    """Форма оформления заказа (без регистрации)."""

    # Контактные данные
    name = forms.CharField(
        label="Ваше имя",
        max_length=120,
        required=True,
        widget=forms.TextInput(attrs={"class": "w-full px-4 py-2.5 border rounded-xl focus:ring-2 focus:ring-[#3d7a4f] focus:border-transparent", "placeholder": "Иван Иванов"})
    )
    email = forms.EmailField(
        label="Email для связи",
        required=True,
        widget=forms.EmailInput(attrs={"class": "w-full px-4 py-2.5 border rounded-xl focus:ring-2 focus:ring-[#3d7a4f] focus:border-transparent", "placeholder": "example@email.com"})
    )
    phone = forms.CharField(
        label="Телефон (необязательно)",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full px-4 py-2.5 border rounded-xl focus:ring-2 focus:ring-[#3d7a4f] focus:border-transparent", "placeholder": "+7 (999) 000-00-00"})
    )

    # Адрес доставки
    country = forms.CharField(
        label="Страна",
        max_length=100,
        required=True,
        initial="Россия",
        widget=forms.TextInput(attrs={"class": "w-full px-4 py-2.5 border rounded-xl focus:ring-2 focus:ring-[#3d7a4f] focus:border-transparent"})
    )
    city = forms.CharField(
        label="Город",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"class": "w-full px-4 py-2.5 border rounded-xl focus:ring-2 focus:ring-[#3d7a4f] focus:border-transparent", "placeholder": "Москва"})
    )
    address = forms.CharField(
        label="Адрес (улица, дом, квартира — необязательно)",
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={"class": "w-full px-4 py-2.5 border rounded-xl focus:ring-2 focus:ring-[#3d7a4f] focus:border-transparent", "rows": 3, "placeholder": "Можно оставить пустым или указать позже"})
    )
    postal_code = forms.CharField(
        label="Почтовый индекс",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full px-4 py-2.5 border rounded-xl focus:ring-2 focus:ring-[#3d7a4f] focus:border-transparent", "placeholder": "101000"})
    )

    # Комментарий
    notes = forms.CharField(
        label="Комментарий к заказу (необязательно)",
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={"class": "w-full px-4 py-2.5 border rounded-xl focus:ring-2 focus:ring-[#3d7a4f] focus:border-transparent", "rows": 3, "placeholder": "Пожелания к заказу"})
    )

    # Согласие на обработку ПДн
    pd_consent = forms.BooleanField(
        label="",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "w-4 h-4 text-[#3d7a4f] border-gray-300 rounded focus:ring-[#3d7a4f]"})
    )

    # Подтверждение ознакомления с лицензионной памяткой (баннер на checkout)
    license_ack = forms.BooleanField(
        label="",
        required=True,
    )

    def clean_pd_consent(self):
        """Проверка согласия на обработку ПДн."""
        consent = self.cleaned_data.get("pd_consent")
        if not consent:
            raise forms.ValidationError(
                "Для оформления заказа необходимо согласие на обработку персональных данных."
            )
        return consent

    def clean_license_ack(self):
        """Проверка подтверждения ознакомления с ограничениями лицензии."""
        ack = self.cleaned_data.get("license_ack")
        if not ack:
            raise forms.ValidationError(
                "Для оформления заказа необходимо подтвердить ознакомление "
                "с условиями личного использования модели."
            )
        return ack


class ProductCreateForm(forms.ModelForm):
    """Упрощённая форма добавления товара/бесплатной модели из профиля.

    Это "UI-дружелюбный дубль" ``ProductAdmin``: редактор видит только те
    поля, что реально нужны для новой карточки. Поля, специфичные для
    бесплатных моделей (``free_category``, ``download_url``), показаны
    всегда — форма валидирует их кросс-зависимо по ``kind``.

    Публикацию (``is_published=True``) может выставить только superuser
    или член группы "Editors" — это правило дублирует ``ProductAdmin``
    и обеспечивается видом ``profile_add_product`` (см. ``core/views.py``).
    """

    class Meta:
        model = Product
        fields = (
            "kind",
            "file_type",
            "free_category",
            "title",
            "slug",
            "description",
            "badge",
            "image",
            "alt",
            "price_rub",
            "download_url",
            "is_published",
            "is_sold_out",
            "is_placeholder",
            "display_order",
        )
        widgets = {
            "kind": forms.Select(attrs={"class": _CONTENT_SELECT_CLASS}),
            "file_type": forms.Select(attrs={"class": _CONTENT_SELECT_CLASS}),
            "free_category": forms.Select(attrs={"class": _CONTENT_SELECT_CLASS}),
            "title": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "Название карточки"}),
            "slug": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "my-product (можно оставить пустым)"}),
            "description": forms.Textarea(attrs={"class": _CONTENT_TEXTAREA_CLASS, "rows": 5, "placeholder": "Краткое описание карточки"}),
            "badge": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "NEW / HOT (необязательно)"}),
            "image": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "images/shop/my-product.png"}),
            "alt": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "Alt-текст для картинки"}),
            "price_rub": forms.NumberInput(attrs={"class": _CONTENT_INPUT_CLASS, "min": 0}),
            "download_url": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "https://... или files/free/xxx.zip"}),
            "display_order": forms.NumberInput(attrs={"class": _CONTENT_INPUT_CLASS, "min": 0}),
            "is_published": forms.CheckboxInput(attrs={"class": _CONTENT_CHECKBOX_CLASS}),
            "is_sold_out": forms.CheckboxInput(attrs={"class": _CONTENT_CHECKBOX_CLASS}),
            "is_placeholder": forms.CheckboxInput(attrs={"class": _CONTENT_CHECKBOX_CLASS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        # Для нового товара slug не обязателен — автогенерим из title
        self.fields["slug"].required = False
        # Placeholder-карточка позволяет оставить image/description пустыми
        self.fields["image"].required = False
        self.fields["alt"].required = False
        self.fields["description"].required = False
        # free_category значим только для kind=free, но форма его не
        # обязывает — проверим в clean().
        self.fields["free_category"].required = False

    def clean_slug(self):
        """Автогенерация slug из title, если пользователь его не заполнил."""
        slug = (self.cleaned_data.get("slug") or "").strip()
        if slug:
            return slug
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            return slug
        base = slugify(title, allow_unicode=False) or "product"
        candidate = base[:80]
        i = 2
        while Product.objects.filter(slug=candidate).exists():
            suffix = f"-{i}"
            candidate = (base[: 80 - len(suffix)] + suffix)
            i += 1
            if i > 999:
                raise ValidationError("Не удалось сгенерировать уникальный slug — укажите его вручную.")
        return candidate

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        free_category = cleaned.get("free_category") or ""
        price_rub = cleaned.get("price_rub") or 0
        is_placeholder = cleaned.get("is_placeholder")
        image = (cleaned.get("image") or "").strip()
        download_url = (cleaned.get("download_url") or "").strip()

        if kind == Product.Kind.FREE:
            if not free_category:
                self.add_error(
                    "free_category",
                    "Для бесплатной модели нужно выбрать таб (художественные/хоббийные/технические).",
                )
            cleaned["price_rub"] = 0
            if not is_placeholder and not download_url:
                self.add_error(
                    "download_url",
                    "Для публикации бесплатной модели укажите ссылку на скачивание "
                    "(или включите «Placeholder», чтобы сохранить как заглушку).",
                )
        else:  # SHOP
            # Для магазина free_category не используется — чистим, чтобы не мозолил глаза.
            cleaned["free_category"] = ""
            if not is_placeholder and price_rub <= 0:
                self.add_error(
                    "price_rub",
                    "Для товара магазина укажите цену больше 0 "
                    "(или используйте placeholder-карточку «Скоро»).",
                )

        if not is_placeholder and not image:
            self.add_error(
                "image",
                "Укажите путь к главной картинке — или включите «Placeholder».",
            )

        # Публиковать может только superuser или Editors (см. ProductAdmin
        # и core/permissions.py — единый источник правды).
        wants_publish = bool(cleaned.get("is_published"))
        if wants_publish and self._user is not None and not can_publish_content(self._user):
            self.add_error(
                "is_published",
                "Публиковать товары может только группа Editors или superuser. "
                "Снимите галочку «Опубликовано», чтобы сохранить как черновик.",
            )

        return cleaned


class NewsArticleCreateForm(forms.ModelForm):
    """Упрощённая форма добавления статьи из профиля.

    Дублирует ``NewsArticleAdmin`` в UI-дружелюбном виде. Автор заполняется
    автоматически во вьюхе из ``request.user``; публикация (status=published)
    ограничена теми же правами, что и в админке.
    """

    class Meta:
        model = NewsArticle
        fields = (
            "title",
            "slug",
            "tag",
            "excerpt",
            "content",
            "cover_image",
            "reading_time_minutes",
            "status",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "Заголовок статьи"}),
            "slug": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "my-article (можно оставить пустым)"}),
            "tag": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "Статья / AI / Техника"}),
            "excerpt": forms.Textarea(attrs={"class": _CONTENT_TEXTAREA_CLASS, "rows": 3, "placeholder": "Короткий анонс (до 600 символов)"}),
            "content": forms.Textarea(attrs={"class": _CONTENT_TEXTAREA_CLASS, "rows": 14, "placeholder": "Текст статьи. Поддерживается простая разметка: ## заголовок, - списки, **жирный**, *курсив*, [ссылка](url), ![alt](images/news/...)"}),
            "cover_image": forms.TextInput(attrs={"class": _CONTENT_INPUT_CLASS, "placeholder": "images/news/cover.jpg"}),
            "reading_time_minutes": forms.NumberInput(attrs={"class": _CONTENT_INPUT_CLASS, "min": 1, "max": 240}),
            "status": forms.Select(attrs={"class": _CONTENT_SELECT_CLASS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self.fields["slug"].required = False

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip()
        if slug:
            return slug
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            return slug
        base = slugify(title, allow_unicode=False) or "article"
        candidate = base[:220]
        i = 2
        while NewsArticle.objects.filter(slug=candidate).exists():
            suffix = f"-{i}"
            candidate = (base[: 220 - len(suffix)] + suffix)
            i += 1
            if i > 999:
                raise ValidationError("Не удалось сгенерировать уникальный slug — укажите его вручную.")
        return candidate

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        if (
            status == NewsArticle.Status.PUBLISHED
            and self._user is not None
            and not can_publish_content(self._user)
        ):
            self.add_error(
                "status",
                "Публиковать статьи может только группа Editors или superuser. "
                "Сохраните как «Черновик».",
            )
        return cleaned

