# La gestión de teleconsultas ya no pasa por el Django Admin: el rol
# "admin" de la app usa su propio panel en /panel/consultas/ (ver
# consultations/views.py y consultations/urls.py). Se deja este archivo
# sin registros a propósito — Consultation, IntakeForm y Diagnosis son
# modelos de dominio de la app, no algo pensado para editarse a mano desde
# un admin genérico. La ruta /admin/ de Django sigue activa (ver
# config/urls.py) solo para debugging directo de la base de datos.
