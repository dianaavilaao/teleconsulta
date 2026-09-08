from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from accounts.views import save_accessibility_prefs, signup

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", signup, name="signup"),
    path("accesibilidad/", save_accessibility_prefs, name="save_accessibility_prefs"),
    path("panel/usuarios/", include("accounts.urls")),
    path("", include("consultations.urls")),
]
