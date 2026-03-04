import pathlib
dest = pathlib.Path("D:/Harmoni/templates/comunicaciones/notificaciones_panel.html")
dest.write_text(CONTENT, encoding="utf-8")
print("Template written:", dest)
