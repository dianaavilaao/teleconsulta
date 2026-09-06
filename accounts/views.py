from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .decorators import staff_required
from .forms import AdminUserCreateForm, AdminUserEditForm, SignupForm
from .services.user_management import create_user_with_role, role_of, update_user_role


def signup(request):
    """Alta pública de cuenta (paciente o profesional); ver SignupForm."""
    if request.user.is_authenticated:
        return redirect("consultations:home")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("consultations:home")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})


# ---- Panel de administración (reemplaza a Django Admin, ver Tarea 2/3) -----


@staff_required
def panel_user_list(request):
    users = User.objects.select_related("profile").order_by("username")
    return render(request, "accounts/panel_user_list.html", {"users": users})


@staff_required
def panel_user_create(request):
    if request.method == "POST":
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            create_user_with_role(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["first_name"],
                role=form.cleaned_data["role"],
            )
            messages.success(request, "Usuario creado.")
            return redirect("accounts:panel_user_list")
    else:
        form = AdminUserCreateForm()

    return render(request, "accounts/panel_user_form.html", {"form": form, "editing": False})


@staff_required
def panel_user_edit(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        form = AdminUserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            edited_user = form.save(commit=False)
            new_password = form.cleaned_data.get("password")
            if new_password:
                edited_user.set_password(new_password)
            edited_user.save()
            update_user_role(edited_user, form.cleaned_data["role"])
            messages.success(request, "Usuario actualizado.")
            return redirect("accounts:panel_user_list")
    else:
        form = AdminUserEditForm(instance=user_obj, initial={"role": role_of(user_obj)})

    return render(
        request,
        "accounts/panel_user_form.html",
        {"form": form, "editing": True, "user_obj": user_obj},
    )


@staff_required
@require_POST
def panel_user_deactivate(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)
    if user_obj == request.user:
        messages.error(request, "No puedes desactivar tu propio usuario.")
        return redirect("accounts:panel_user_list")

    user_obj.is_active = False
    user_obj.save(update_fields=["is_active"])
    messages.success(request, f'Usuario "{user_obj.username}" desactivado.')
    return redirect("accounts:panel_user_list")


@staff_required
@require_POST
def panel_user_reactivate(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)
    user_obj.is_active = True
    user_obj.save(update_fields=["is_active"])
    messages.success(request, f'Usuario "{user_obj.username}" reactivado.')
    return redirect("accounts:panel_user_list")
