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
