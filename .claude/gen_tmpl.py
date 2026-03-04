import pathlib
b = "{%"
e = "%}"
out = []
w = out.append

# Header
w(b + " extends \"base.html\" " + e)
w(b + " load humanize " + e)
w("")
w(b + " block title " + e + "Notificaciones" + b + " endblock " + e)
w("")
w(b + " block content " + e)
# KPI helper
def kpi(col, val, label, cls="", color=""):
    sty = " style=\"color:%s;\"" % color if color else ""
    ca = " class=\"fs-3 fw-bold %s\"" % cls if cls else " class=\"fs-3 fw-bold\""
    w("    <div class=\"%s\">" % col)
    w("        <div class=\"card h-100 border-0 shadow-sm\">")
    w("            <div class=\"card-body p-3 text-center\">")
    w("                <div%s%s>%s</div>" % (ca, sty, val))
    w("                <div class=\"small text-muted mt-1\">%s</div>" % label)
    w("            </div>")
    w("        </div>")
    w("    </div>")
    w("")
