from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

User = get_user_model()


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

