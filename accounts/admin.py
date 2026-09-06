# La gestión de usuarios (alta, edición de rol, desactivar/reactivar) ya
# no pasa por el Django Admin: el rol "admin" de la app usa su propio
# panel en /panel/usuarios/ (ver accounts/views.py y accounts/urls.py).
# Al no registrar acá un UserAdmin propio, /admin/ muestra el UserAdmin
# por defecto de django.contrib.auth — suficiente para debugging directo
# de la base de datos, que es lo único para lo que se deja /admin/ activo.
