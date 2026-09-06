from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.panel_user_list, name="panel_user_list"),
    path("nuevo/", views.panel_user_create, name="panel_user_create"),
    path("<int:user_id>/editar/", views.panel_user_edit, name="panel_user_edit"),
    path("<int:user_id>/desactivar/", views.panel_user_deactivate, name="panel_user_deactivate"),
    path("<int:user_id>/reactivar/", views.panel_user_reactivate, name="panel_user_reactivate"),
]
