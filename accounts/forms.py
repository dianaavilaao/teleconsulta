from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import UserProfile
from .services.user_management import ROLE_CHOICES


class SignupForm(UserCreationForm):
    """
    Alta pública de cuenta (paciente o profesional). El rol "admin" no es
    una opción aquí a propósito: se sigue reservando a `user.is_staff`,
    otorgado solo desde el Django Admin — no es algo que alguien deba
    poder autoasignarse desde un formulario público.
    """

    first_name = forms.CharField(label="Nombre completo", max_length=150, required=False)
    role = forms.ChoiceField(label="Tipo de cuenta", choices=UserProfile.Role.choices)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name"]

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            UserProfile.objects.create(user=user, role=self.cleaned_data["role"])
        return user


class AdminUserCreateForm(forms.Form):
    """Alta de usuario desde el panel de admin (/panel/usuarios/nuevo/), con rol elegible incluyendo "admin"."""

    username = forms.CharField(label="Usuario", max_length=150)
    first_name = forms.CharField(label="Nombre completo", max_length=150, required=False)
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    role = forms.ChoiceField(label="Rol", choices=ROLE_CHOICES)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre de usuario.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password


class AdminUserEditForm(forms.ModelForm):
    """
    Edición desde el panel de admin: nombre, rol, y contraseña opcional
    (vacía = no cambiarla). `role` no es un campo de User, se precarga con
    `initial` desde la vista (ver role_of en services/user_management.py).
    """

    password = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput,
        required=False,
        help_text="Déjalo vacío para no cambiarla.",
    )
    role = forms.ChoiceField(label="Rol", choices=ROLE_CHOICES)

    class Meta:
        model = User
        fields = ["username", "first_name"]

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre de usuario.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password, user=self.instance)
        return password
