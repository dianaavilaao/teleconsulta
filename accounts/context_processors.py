"""
Context processor que arma las clases de accesibilidad para <html> del
lado del servidor, para que la página ya salga correcta al cargar (sin
esperar al JS, que solo entra en juego para reaccionar a clicks del
usuario o para el caso anónimo — ver templates/base.html).
"""


def accessibility(request):
    if not request.user.is_authenticated:
        return {"a11y_classes": ""}

    prefs = getattr(request.user, "accessibility_prefs", None)
    if prefs is None:
        return {"a11y_classes": ""}

    classes = []
    if prefs.font_scale == "lg":
        classes.append("a11y-font-lg")
    elif prefs.font_scale == "xl":
        classes.append("a11y-font-xl")
    if prefs.high_contrast:
        classes.append("a11y-high-contrast")
    if prefs.reduce_motion:
        classes.append("a11y-reduce-motion")

    return {"a11y_classes": " ".join(classes)}
