from __future__ import annotations
import datetime
import random
import traceback
import unicodedata
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

G  = "\033[92m"
Y  = "\033[93m"
C  = "\033[96m"
R  = "\033[91m"
B  = "\033[1m"
X  = "\033[0m"


def ok(m):     print(G + "  OK  " + X + str(m))
def warn(m):   print(R + "  !!  " + X + str(m))
def hdr(m):    print(B + C + "-" * 60 + X + "\n" + B + "  " + m + X + "\n" + B + C + "-" * 60 + X)
def step(n, m): print("\n" + B + "[" + str(n) + "]" + X + " " + Y + m + X)


def _slug(s):
    """Normaliza string a minusculas sin tildes ni espacios."""
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").lower().replace(" ", "")


DOCS = [
    "43251876", "47832910", "40123456", "72345019", "44567823",
    "76543210", "75019283", "48291037", "39871024", "52019384",
    "43918274", "47019283", "60123748", "44019273", "71028374",
]

# Columnas: doc, apellidos_nombres, cargo, tipo_trab, grupo_tareo,
#           area, subarea, sexo, sueldo, estado, categoria,
#           regimen_pension, afp, tipo_contrato, condicion, anio_ingreso
PERSONAL_DATA = [
    ("43251876", "Rios Mamani, Juan Carlos",        "Operador Mina",           "Obrero",   "RCO",
     "Operaciones",     "Mina",           "M",  2400, "Activo",  "NORMAL",    "AFP", "Prima",     "OBRA_SERVICIO", "FORANEO", 2023),
    ("47832910", "Condori Huanca, Luis Alberto",    "Operador Mina",           "Obrero",   "RCO",
     "Operaciones",     "Mina",           "M",  2600, "Activo",  "NORMAL",    "AFP", "Integra",   "OBRA_SERVICIO", "FORANEO", 2022),
    ("40123456", "Ramirez Torres, Pedro Andres",    "Supervisor de Mina",      "Empleado", "STAFF",
     "Operaciones",     "Mina",           "M",  5200, "Activo",  "NORMAL",    "AFP", "Habitat",   "INDEFINIDO",    "FORANEO", 2020),
    ("72345019", "Huanca Apaza, Miguel Angel",      "Operador Planta",         "Obrero",   "RCO",
     "Operaciones",     "Planta",         "M",  2200, "Activo",  "NORMAL",    "ONP", None,        "PLAZO_FIJO",    "FORANEO", 2024),
    ("44567823", "Flores Quispe, Carmen Rosa",      "Operador Planta",         "Obrero",   "RCO",
     "Operaciones",     "Planta",         "F",  2200, "Activo",  "NORMAL",    "ONP", None,        "PLAZO_FIJO",    "LOCAL",   2024),
    ("76543210", "Ticona Mamani, Rosa Maria",       "Tecnico de Planta",       "Obrero",   "RCO",
     "Operaciones",     "Planta",         "F",  2800, "Activo",  "NORMAL",    "AFP", "Profuturo", "INDEFINIDO",    "LOCAL",   2021),
    ("75019283", "Vargas Cano, Carlos Eduardo",     "Tecnico Mantenimiento",   "Obrero",   "RCO",
     "Operaciones",     "Mantenimiento",  "M",  2800, "Activo",  "NORMAL",    "AFP", "Prima",     "INDEFINIDO",    "FORANEO", 2021),
    ("48291037", "Mamani Quispe, Jorge Luis",       "Tecnico Mantenimiento",   "Obrero",   "RCO",
     "Operaciones",     "Mantenimiento",  "M",  2600, "Activo",  "NORMAL",    "AFP", "Integra",   "PLAZO_FIJO",    "FORANEO", 2023),
    ("39871024", "Gutierrez Salas, Maria Elena",    "Analista de RRHH",        "Empleado", "STAFF",
     "Administracion",  "RRHH",           "F",  3800, "Activo",  "NORMAL",    "AFP", "Habitat",   "INDEFINIDO",    "LIMA",    2021),
    ("52019384", "Mendez Paredes, Ana Lucia",       "Coordinadora de RRHH",    "Empleado", "STAFF",
     "Administracion",  "RRHH",           "F",  4500, "Activo",  "NORMAL",    "AFP", "Prima",     "INDEFINIDO",    "LIMA",    2019),
    ("43918274", "Pinto Huanca, Roberto Carlos",    "Contador Senior",         "Empleado", "STAFF",
     "Administracion",  "Contabilidad",   "M",  5800, "Activo",  "NORMAL",    "AFP", "Profuturo", "INDEFINIDO",    "LIMA",    2018),
    ("47019283", "Yupanqui Cano, Sandra Patricia",  "Asistente de Logistica",  "Empleado", "STAFF",
     "Administracion",  "Logistica",      "F",  2800, "Activo",  "NORMAL",    "AFP", "Integra",   "PLAZO_FIJO",    "LIMA",    2023),
    ("60123748", "Morales Arce, Fernando Jose",     "Jefe de Logistica",       "Empleado", "STAFF",
     "Administracion",  "Logistica",      "M",  6500, "Activo",  "NORMAL",    "AFP", "Habitat",   "INDEFINIDO",    "LIMA",    2017),
    ("44019273", "Solis Quispe, Patricia Isabel",   "Secretaria de Gerencia",  "Empleado", "STAFF",
     "Gerencia",        "Direccion",      "F",  3200, "Activo",  "NORMAL",    "AFP", "Prima",     "INDEFINIDO",    "LIMA",    2020),
    ("71028374", "Torres Mamani, Eduardo Alberto",  "Gerente General",         "Empleado", "STAFF",
     "Gerencia",        "Direccion",      "M", 12000, "Activo",  "CONFIANZA", "AFP", "Profuturo", "INDEFINIDO",    "LIMA",    2015),
]


class Command(BaseCommand):
    help = "Pobla la BD con datos de prueba realistas para Harmoni ERP"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar", action="store_true",
            help="Elimina datos previos antes de poblar",
        )

    def handle(self, *args, **options):
        hdr("HARMONI ERP - Poblar Datos de Prueba")
        if options["limpiar"]:
            self._limpiar()
        empresa  = self._empresa()
        self._config(empresa)
        areas    = self._areas()
        personal = self._personal(areas, empresa)
        self._usuario(personal)
        self._conceptos()
        periodo  = self._periodo(empresa)
        activos  = [p for p in personal if p.estado == "Activo"]
        self._nomina(periodo, activos)
        self._tareo(activos)
        self._vacantes(areas)
        self._vacaciones(activos)
        self._saldo_vacacional(activos)
        self._prestamos(activos)
        hdr("COMPLETADO")
        print("  Personal    : " + str(len(personal)) + " total, " + str(len(activos)) + " activos")
        print("  Login portal: trabajador / Harmoni2026!")
        print("  Admin       : admin / Admin2026!")
        print("")

    # ------------------------------------------------------------------ #
    #  0. LIMPIAR                                                          #
    # ------------------------------------------------------------------ #
    def _limpiar(self):
        step(0, "Limpiando datos previos...")
        try:
            from vacaciones.models import SolicitudVacacion
            n = SolicitudVacacion.objects.all().delete()[0]
            ok("SolicitudVacacion eliminadas: " + str(n))
        except Exception as e:
            warn("vacaciones: " + str(e))
        try:
            from reclutamiento.models import Vacante
            Vacante.objects.filter(
                titulo__in=["Operador Mina", "Contador Senior", "Analista RRHH"]
            ).delete()
            ok("Vacantes de prueba eliminadas")
        except Exception as e:
            warn("reclutamiento: " + str(e))
        try:
            from nominas.models import RegistroNomina, PeriodoNomina
            RegistroNomina.objects.all().delete()
            PeriodoNomina.objects.filter(anio=2026, mes=2).delete()
            ok("Nomina 2026-02 eliminada")
        except Exception as e:
            warn("nominas: " + str(e))
        try:
            from asistencia.models import TareoImportacion
            TareoImportacion.objects.filter(archivo_nombre="datos_prueba").delete()
            ok("TareoImportacion prueba eliminada")
        except Exception as e:
            warn("asistencia: " + str(e))
        try:
            from personal.models import Personal
            Personal.objects.filter(nro_doc__in=DOCS).delete()
            ok("Personal de prueba eliminado")
        except Exception as e:
            warn("personal: " + str(e))
        try:
            from empresas.models import Empresa
            Empresa.objects.filter(ruc="20123456789").delete()
            ok("Empresa eliminada")
        except Exception as e:
            warn("empresas: " + str(e))

    # ------------------------------------------------------------------ #
    #  1. EMPRESA                                                          #
    # ------------------------------------------------------------------ #
    def _empresa(self):
        step(1, "Empresa principal...")
        from empresas.models import Empresa
        emp, c = Empresa.objects.get_or_create(
            ruc="20123456789",
            defaults={
                "razon_social":        "Minera Andes SAC",
                "nombre_comercial":    "Andes Mining",
                "direccion":           "Av. Javier Prado Este 4600, Lima",
                "distrito":            "Surco",
                "provincia":           "Lima",
                "departamento":        "Lima",
                "telefono":            "(01) 234-5678",
                "email_rrhh":          "rrhh@andesminera.com.pe",
                "regimen_laboral":     "GENERAL",
                "sector":              "PRIVADO",
                "actividad_economica": "CIIU 0710 - Extraccion minerales",
                "activa":              True,
                "es_principal":        True,
            },
        )
        ok(("Creada" if c else "Ya existe") + ": Minera Andes SAC (RUC 20123456789)")
        return emp

    # ------------------------------------------------------------------ #
    #  2. CONFIGURACION SISTEMA                                            #
    # ------------------------------------------------------------------ #
    def _config(self, empresa):
        step(2, "ConfiguracionSistema...")
        try:
            from asistencia.models import ConfiguracionSistema
            cfg, c = ConfiguracionSistema.objects.get_or_create(pk=1)
            cfg.empresa_nombre    = "Minera Andes SAC"
            cfg.ruc               = "20123456789"
            cfg.empresa_direccion = "Av. Javier Prado Este 4600, Surco, Lima"
            cfg.empresa_email     = "rrhh@andesminera.com.pe"
            cfg.empresa_telefono  = "(01) 234-5678"
            cfg.modo_sistema      = "ERP_COMPLETO"
            for attr in (
                "mod_prestamos", "mod_viaticos", "mod_documentos",
                "mod_evaluaciones", "mod_capacitaciones",
                "mod_reclutamiento", "mod_encuestas", "mod_salarios",
            ):
                setattr(cfg, attr, True)
            cfg.save()
            ok(("Creada" if c else "Actualizada") + ": ConfiguracionSistema ERP_COMPLETO")
        except Exception as e:
            warn("ConfiguracionSistema: " + str(e))

    # ------------------------------------------------------------------ #
    #  3. AREAS Y SUBAREAS                                                 #
    # ------------------------------------------------------------------ #
    def _areas(self):
        step(3, "Areas y SubAreas...")
        from personal.models import Area, SubArea
        estructura = {
            "Operaciones":    ["Mina", "Planta", "Mantenimiento"],
            "Administracion": ["RRHH", "Contabilidad", "Logistica"],
            "Gerencia":       ["Direccion"],
        }
        areas = {}
        for na, subs in estructura.items():
            a, _ = Area.objects.get_or_create(nombre=na, defaults={"activa": True})
            areas[na] = {"area": a, "subareas": {}}
            for ns in subs:
                s, _ = SubArea.objects.get_or_create(nombre=ns, area=a, defaults={"activa": True})
                areas[na]["subareas"][ns] = s
                ok("  " + na + " -> " + ns)
        return areas

    # ------------------------------------------------------------------ #
    #  4. PERSONAL (15 empleados)                                          #
    # ------------------------------------------------------------------ #
    def _personal(self, areas, empresa):
        step(4, "Personal (15 empleados)...")
        from personal.models import Personal
        creados = []
        for row in PERSONAL_DATA:
            (doc, nombre, cargo, tipo_trab, grupo,
             area_n, subarea_n, sexo, sueldo,
             estado, categoria, regimen, afp,
             tipo_c, condicion, anio) = row

            subarea    = areas[area_n]["subareas"][subarea_n]
            fecha_alta = datetime.date(anio, random.randint(1, 12), random.randint(1, 28))

            # Build correo from nombres
            partes   = nombre.split(",")
            apellido = _slug(partes[0].strip())[:14]
            pnombre  = _slug(partes[1].strip().split()[0]) if len(partes) > 1 else doc
            correo   = pnombre + "." + apellido + "@andesminera.com.pe"
            celular  = "9" + str(random.randint(10_000_000, 99_999_999))

            defaults = {
                "apellidos_nombres": nombre,
                "cargo":             cargo,
                "tipo_trab":         tipo_trab,
                "grupo_tareo":       grupo,
                "sexo":              sexo,
                "sueldo_base":       Decimal(str(sueldo)),
                "estado":            estado,
                "categoria":         categoria,
                "regimen_pension":   regimen,
                "tipo_contrato":     tipo_c,
                "condicion":         condicion,
                "fecha_alta":        fecha_alta,
                "subarea":           subarea,
                "empresa":           empresa,
                "correo_corporativo": correo,
                "celular":           celular,
            }
            if afp:
                defaults["afp"] = afp

            p, c = Personal.objects.get_or_create(nro_doc=doc, defaults=defaults)
            creados.append(p)
            ok(("  Creado" if c else "  Existe") + ": " + nombre + " [" + grupo + " | " + regimen + "]")
        return creados

    # ------------------------------------------------------------------ #
    #  5. USUARIOS SISTEMA                                                 #
    # ------------------------------------------------------------------ #
    def _usuario(self, personal):
        step(5, "Usuarios sistema...")

        # Admin superuser
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                "admin", "admin@andesminera.com.pe", "Admin2026!"
            )
            ok("Creado superuser: admin / Admin2026!")
        else:
            ok("Ya existe: admin")

        # Portal worker — linked to Maria Elena Gutierrez (STAFF, RRHH)
        trabajador_doc = "39871024"
        if not User.objects.filter(username="trabajador").exists():
            u = User.objects.create_user(
                "trabajador", "mgutierrez@andesminera.com.pe", "Harmoni2026!"
            )
            u.first_name = "Maria Elena"
            u.last_name  = "Gutierrez Salas"
            u.save()
            ok("Creado user: trabajador / Harmoni2026!")
        else:
            u = User.objects.get(username="trabajador")
            ok("Ya existe: trabajador")

        # Vincular usuario -> Personal
        try:
            from personal.models import Personal
            p = Personal.objects.filter(nro_doc=trabajador_doc).first()
            if p:
                # Check if 'usuario' field exists on model
                p.__class__._meta.get_field("usuario")
                if not p.usuario_id:
                    p.usuario = u
                    p.save(update_fields=["usuario"])
                    ok("Vinculado: trabajador -> " + p.apellidos_nombres)
                else:
                    ok("Ya vinculado: " + p.apellidos_nombres)
        except Exception as e:
            warn("Link usuario-personal: " + str(e))

    # ------------------------------------------------------------------ #
    #  6. CONCEPTOS REMUNERATIVOS                                          #
    # ------------------------------------------------------------------ #
    def _conceptos(self):
        step(6, "ConceptosRemunerativos...")
        try:
            from nominas.models import ConceptoRemunerativo
            # (codigo, nombre, tipo, subtipo, formula, pct, ess, renta, cts, grat, orden)
            conceptos = [
                ("SUELDO_BAS",   "Sueldo Basico",            "INGRESO",          "REMUNERATIVO",  "FIJO",        Decimal("0"),    True,  True,  True,  True,   1),
                ("ASIG_FAM",     "Asignacion Familiar",      "INGRESO",          "REMUNERATIVO",  "FIJO",        Decimal("0"),    True,  True,  True,  True,   2),
                ("HE_25",        "Horas Extra 25%",          "INGRESO",          "REMUNERATIVO",  "HE_25",       Decimal("25"),   True,  True,  True,  True,   5),
                ("HE_35",        "Horas Extra 35%",          "INGRESO",          "REMUNERATIVO",  "HE_35",       Decimal("35"),   True,  True,  True,  True,   6),
                ("HE_100",       "Horas Extra 100%",         "INGRESO",          "REMUNERATIVO",  "HE_100",      Decimal("100"),  False, True,  False, False,  7),
                ("AFP_APORTE",   "AFP Aporte Obligatorio",   "DESCUENTO",        "REMUNERATIVO",  "AFP_APORTE",  Decimal("10"),   False, False, False, False, 10),
                ("AFP_COMISION", "AFP Comision Mixta",       "DESCUENTO",        "REMUNERATIVO",  "AFP_COMISION",Decimal("1.74"), False, False, False, False, 11),
                ("AFP_SEGURO",   "AFP Seguro de Invalidez",  "DESCUENTO",        "REMUNERATIVO",  "AFP_SEGURO",  Decimal("1.84"), False, False, False, False, 12),
                ("ONP",          "ONP Aporte",               "DESCUENTO",        "REMUNERATIVO",  "ONP",         Decimal("13"),   False, False, False, False, 13),
                ("ESSALUD",      "EsSalud Aporte Empleador", "APORTE_EMPLEADOR", "REMUNERATIVO",  "ESSALUD",     Decimal("9"),    False, False, False, False, 20),
            ]
            for (codigo, nombre, tipo, subtipo, formula, pct,
                 afecto_e, afecto_r, afecto_c, afecto_g, orden) in conceptos:
                obj, c = ConceptoRemunerativo.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        "nombre":        nombre,
                        "tipo":          tipo,
                        "subtipo":       subtipo,
                        "formula":       formula,
                        "porcentaje":    pct,
                        "afecto_essalud": afecto_e,
                        "afecto_renta":  afecto_r,
                        "afecto_cts":    afecto_c,
                        "afecto_gratif": afecto_g,
                        "es_sistema":    True,
                        "activo":        True,
                        "orden":         orden,
                    },
                )
                ok(("  Creado" if c else "  Existe") + ": " + codigo + " - " + nombre)
        except Exception as e:
            warn("Conceptos: " + str(e))
            traceback.print_exc()

    # ------------------------------------------------------------------ #
    #  7. PERIODO NOMINA FEB 2026                                          #
    # ------------------------------------------------------------------ #
    def _periodo(self, empresa):
        step(7, "PeriodoNomina 2026-02...")
        try:
            from nominas.models import PeriodoNomina
            admin_u = User.objects.filter(is_superuser=True).first()
            p, c = PeriodoNomina.objects.get_or_create(
                anio=2026,
                mes=2,
                defaults={
                    "tipo":         "REGULAR",
                    "fecha_inicio": datetime.date(2026, 1, 21),
                    "fecha_fin":    datetime.date(2026, 2, 20),
                    "fecha_pago":   datetime.date(2026, 2, 28),
                    "estado":       "CALCULADO",
                    "empresa":      empresa,
                    "generado_por": admin_u,
                },
            )
            ok(("Creado" if c else "Ya existe") + ": Periodo Feb 2026 (21-ene -> 20-feb)")
            return p
        except Exception as e:
            warn("PeriodoNomina: " + str(e))
            traceback.print_exc()
            return None

    # ------------------------------------------------------------------ #
    #  8. REGISTROS DE NOMINA                                              #
    # ------------------------------------------------------------------ #
    def _nomina(self, periodo, activos):
        step(8, "Registros de Nomina Feb 2026...")
        if not periodo:
            warn("Sin periodo — saltando nomina")
            return
        try:
            from nominas.models import RegistroNomina, LineaNomina, ConceptoRemunerativo

            # Prefetch conceptos
            def conc(codigo):
                return ConceptoRemunerativo.objects.filter(codigo=codigo).first()

            c_sueldo = conc("SUELDO_BAS")
            c_afp_a  = conc("AFP_APORTE")
            c_afp_c  = conc("AFP_COMISION")
            c_afp_s  = conc("AFP_SEGURO")
            c_onp    = conc("ONP")
            c_ess    = conc("ESSALUD")

            Q = Decimal("0.01")

            for p in activos:
                sueldo = p.sueldo_base or Decimal("0")
                if sueldo == 0:
                    warn("  Sin sueldo_base: " + p.apellidos_nombres)
                    continue

                if p.regimen_pension == "AFP":
                    desc_afp_a = (sueldo * Decimal("0.10")).quantize(Q)
                    desc_afp_c = (sueldo * Decimal("0.0174")).quantize(Q)
                    desc_afp_s = (sueldo * Decimal("0.0184")).quantize(Q)
                    total_desc = desc_afp_a + desc_afp_c + desc_afp_s
                    desc_onp   = Decimal("0")
                else:
                    desc_afp_a = desc_afp_c = desc_afp_s = Decimal("0")
                    desc_onp   = (sueldo * Decimal("0.13")).quantize(Q)
                    total_desc = desc_onp

                essalud   = (sueldo * Decimal("0.09")).quantize(Q)
                neto      = (sueldo - total_desc).quantize(Q)

                reg, c = RegistroNomina.objects.get_or_create(
                    periodo=periodo,
                    personal=p,
                    defaults={
                        "sueldo_base":         sueldo,
                        "regimen_pension":     p.regimen_pension,
                        "afp":                 p.afp or "",
                        "grupo":               p.grupo_tareo,
                        "dias_trabajados":     30,
                        "dias_descanso":       0,
                        "dias_falta":          0,
                        "total_ingresos":      sueldo,
                        "total_descuentos":    total_desc,
                        "neto_a_pagar":        neto,
                        "aporte_essalud":      essalud,
                        "costo_total_empresa": sueldo + essalud,
                        "estado":              "CALCULADO",
                    },
                )

                if c:
                    # Lineas de nomina
                    def linea(concepto, monto, base, pct):
                        if concepto:
                            LineaNomina.objects.get_or_create(
                                registro=reg, concepto=concepto,
                                defaults={
                                    "monto":               monto,
                                    "base_calculo":        base,
                                    "porcentaje_aplicado": pct,
                                },
                            )

                    linea(c_sueldo, sueldo,    sueldo, Decimal("0"))
                    linea(c_ess,    essalud,   sueldo, Decimal("9"))

                    if p.regimen_pension == "AFP":
                        linea(c_afp_a, desc_afp_a, sueldo, Decimal("10"))
                        linea(c_afp_c, desc_afp_c, sueldo, Decimal("1.74"))
                        linea(c_afp_s, desc_afp_s, sueldo, Decimal("1.84"))
                    else:
                        linea(c_onp, desc_onp, sueldo, Decimal("13"))

                ok(
                    ("  Creado" if c else "  Existe") + ": " +
                    p.apellidos_nombres + "  S/ " + str(neto) + " neto"
                )
        except Exception as e:
            warn("Nomina: " + str(e))
            traceback.print_exc()

    # ------------------------------------------------------------------ #
    #  9. TAREO / ASISTENCIA FEB 2026                                      #
    # ------------------------------------------------------------------ #
    def _tareo(self, activos):
        step(9, "Tareo Asistencia Feb 2026...")
        try:
            from asistencia.models import TareoImportacion, RegistroTareo

            # Días hábiles de febrero 2026 (lun-vie)
            working_days = []
            d = datetime.date(2026, 2, 2)
            while d <= datetime.date(2026, 2, 28):
                if d.weekday() < 5:
                    working_days.append(d)
                d += datetime.timedelta(days=1)

            n_exp = len(activos) * len(working_days)
            imp, c = TareoImportacion.objects.get_or_create(
                archivo_nombre="datos_prueba",
                defaults={
                    "tipo":           "PAPELETAS",
                    "periodo_inicio": datetime.date(2026, 2, 2),
                    "periodo_fin":    datetime.date(2026, 2, 28),
                    "estado":         "COMPLETADO",
                    "total_registros": n_exp,
                    "registros_ok":   n_exp,
                    "registros_error": 0,
                },
            )
            ok(("Creada" if c else "Existe") + ": TareoImportacion datos_prueba (" + str(len(working_days)) + " dias habiles)")

            creados = 0
            for p in activos:
                for dia in working_days:
                    # 5% probabilidad de falta (solo para no-CONFIANZA)
                    ausente = (
                        p.categoria not in ("CONFIANZA", "DIRECCION")
                        and random.random() < 0.05
                    )
                    codigo  = "F" if ausente else "A"
                    he_25   = Decimal("0")
                    he_100  = Decimal("0")
                    if not ausente and p.categoria not in ("CONFIANZA", "DIRECCION"):
                        # RCO: 30% chance de 2 HE25 por día
                        if p.grupo_tareo == "RCO" and random.random() < 0.3:
                            he_25 = Decimal("2")
                        # RCO domingos: HE100 (aunque generamos solo lun-vie)

                    _, cr = RegistroTareo.objects.get_or_create(
                        importacion=imp,
                        personal=p,
                        fecha=dia,
                        defaults={
                            "dni":           p.nro_doc,
                            "grupo":         p.grupo_tareo,
                            "condicion":     p.condicion or "LOCAL",
                            "codigo_dia":    codigo,
                            "fuente_codigo": "PAPELETA",
                            "horas_normales": Decimal("0") if ausente else Decimal("8"),
                            "he_25":          he_25,
                            "he_35":          Decimal("0"),
                            "he_100":         he_100,
                        },
                    )
                    if cr:
                        creados += 1

            ok("RegistroTareo creados: " + str(creados) + " / " + str(n_exp))
        except Exception as e:
            warn("Tareo: " + str(e))
            traceback.print_exc()

    # ------------------------------------------------------------------ #
    # 10. VACANTES ABIERTAS                                                #
    # ------------------------------------------------------------------ #
    def _vacantes(self, areas):
        step(10, "Vacantes abiertas...")
        try:
            from reclutamiento.models import Vacante
            vacantes = [
                {
                    "titulo":          "Operador Mina",
                    "area":            areas["Operaciones"]["area"],
                    "descripcion":     (
                        "Buscamos Operador de Mina con experiencia en mineria subterranea. "
                        "Requisitos: 2+ anos experiencia, licencia vigente, regimen 14x7."
                    ),
                    "requisitos":      (
                        "- Experiencia minima 2 anos en mina subterranea\n"
                        "- Disponibilidad para trabajar en regimen 14x7\n"
                        "- Licencia de conducir clase A2"
                    ),
                    "salario_min":     Decimal("2200"),
                    "salario_max":     Decimal("2800"),
                    "estado":          "PUBLICADA",
                    "prioridad":       "ALTA",
                    "tipo_contrato":   "PROYECTO",
                    "educacion_minima": "SECUNDARIA",
                    "publica":         True,
                },
                {
                    "titulo":          "Contador Senior",
                    "area":            areas["Administracion"]["area"],
                    "descripcion":     (
                        "Requerimos Contador Senior para fortalecer el equipo de Contabilidad. "
                        "Manejo de SUNAT, PDT, cierre mensual y contabilidad minera."
                    ),
                    "requisitos":      (
                        "- Titulo de Contador Publico Colegiado\n"
                        "- Experiencia 5+ anos en empresas mineras\n"
                        "- Manejo de PDT 601/621 y SUNAT Operaciones en Linea"
                    ),
                    "salario_min":     Decimal("5500"),
                    "salario_max":     Decimal("7000"),
                    "estado":          "EN_PROCESO",
                    "prioridad":       "MEDIA",
                    "tipo_contrato":   "INDETERMINADO",
                    "educacion_minima": "UNIVERSITARIO",
                    "publica":         True,
                },
                {
                    "titulo":          "Analista RRHH",
                    "area":            areas["Administracion"]["area"],
                    "descripcion":     (
                        "Buscamos Analista de RRHH para procesos de nomina, seleccion "
                        "y bienestar. Experiencia en ERP RRHH deseable."
                    ),
                    "requisitos":      (
                        "- Carrera de Administracion o RRHH\n"
                        "- Experiencia 2+ anos en gestion de RRHH\n"
                        "- Conocimiento de legislacion laboral peruana"
                    ),
                    "salario_min":     Decimal("3200"),
                    "salario_max":     Decimal("4200"),
                    "estado":          "PUBLICADA",
                    "prioridad":       "MEDIA",
                    "tipo_contrato":   "INDETERMINADO",
                    "educacion_minima": "UNIVERSITARIO",
                    "publica":         True,
                },
            ]
            for v in vacantes:
                obj, c = Vacante.objects.get_or_create(titulo=v["titulo"], defaults=v)
                ok(("  Creada" if c else "  Existe") + ": " + v["titulo"] + " [" + v["estado"] + "]")
        except Exception as e:
            warn("Vacantes: " + str(e))
            traceback.print_exc()

    # ------------------------------------------------------------------ #
    # 11. SOLICITUDES DE VACACIONES                                        #
    # ------------------------------------------------------------------ #
    def _vacaciones(self, activos):
        step(11, "Solicitudes de Vacaciones...")
        try:
            from vacaciones.models import SolicitudVacacion

            # Filtrar solo STAFF para vacaciones
            staff = [p for p in activos if p.grupo_tareo == "STAFF"]
            if len(staff) < 3:
                staff = activos[:3]

            # (indice, fecha_inicio, fecha_fin, estado)
            requests = [
                (0, datetime.date(2026, 1, 6),  datetime.date(2026, 1, 15), "COMPLETADA"),
                (1, datetime.date(2026, 3, 3),  datetime.date(2026, 3, 12), "APROBADA"),
                (2, datetime.date(2026, 3, 20), datetime.date(2026, 3, 27), "PENDIENTE"),
            ]
            if len(staff) > 3:
                requests.append((3, datetime.date(2026, 4, 7), datetime.date(2026, 4, 16), "PENDIENTE"))

            for idx, ini, fin, estado in requests:
                if idx >= len(staff):
                    continue
                personal = staff[idx]
                dias = (fin - ini).days + 1
                qs = SolicitudVacacion.objects.filter(personal=personal, fecha_inicio=ini)
                if qs.exists():
                    ok("  Existe: " + personal.apellidos_nombres + " " + str(ini))
                    continue
                SolicitudVacacion.objects.create(
                    personal=personal,
                    fecha_inicio=ini,
                    fecha_fin=fin,
                    dias_calendario=dias,
                    estado=estado,
                )
                ok(
                    "  Creada: " + personal.apellidos_nombres +
                    "  " + str(ini) + " -> " + str(fin) +
                    "  [" + estado + "]"
                )
        except Exception as e:
            warn("Vacaciones: " + str(e))
            traceback.print_exc()

    # ------------------------------------------------------------------ #
    # 12. SALDO VACACIONAL (derecho legal)                                 #
    # ------------------------------------------------------------------ #
    def _saldo_vacacional(self, activos):
        step(12, "Saldos Vacacionales...")
        try:
            from vacaciones.models import SaldoVacacional
            # Período aniversario actual: año de ingreso → año siguiente
            for p in activos:
                if not p.fecha_alta:
                    continue
                anio_alta = p.fecha_alta.year
                mes_alta  = p.fecha_alta.month
                dia_alta  = p.fecha_alta.day
                # Último período aniversario completado antes de hoy
                try:
                    periodo_ini = datetime.date(2025, mes_alta, dia_alta)
                    periodo_fin = datetime.date(2026, mes_alta, dia_alta) - datetime.timedelta(days=1)
                except ValueError:
                    periodo_ini = datetime.date(2025, mes_alta, 28)
                    periodo_fin = datetime.date(2026, mes_alta, 27)

                # Días de derecho según antigüedad (D.Leg 713: 30 días/año)
                anios = max(1, 2026 - anio_alta)
                dias_derecho = 30  # estándar Perú

                # Días gozados = los que tienen solicitud COMPLETADA
                dias_gozados = 0
                try:
                    from vacaciones.models import SolicitudVacacion
                    dias_gozados = sum(
                        sv.dias_calendario
                        for sv in SolicitudVacacion.objects.filter(
                            personal=p, estado__in=("COMPLETADA", "EN_GOCE")
                        )
                        if sv.dias_calendario
                    )
                except Exception:
                    pass

                dias_pendientes = max(0, dias_derecho - dias_gozados)

                qs = SaldoVacacional.objects.filter(personal=p, periodo_inicio=periodo_ini)
                if qs.exists():
                    ok("  Existe: " + p.apellidos_nombres)
                    continue
                SaldoVacacional.objects.create(
                    personal=p,
                    periodo_inicio=periodo_ini,
                    periodo_fin=periodo_fin,
                    dias_derecho=dias_derecho,
                    dias_gozados=min(dias_gozados, dias_derecho),
                    dias_vendidos=0,
                    dias_pendientes=dias_pendientes,
                    dias_truncos=Decimal("0"),
                    estado="VIGENTE",
                )
                ok("  Creado: " + p.apellidos_nombres + "  disponibles=" + str(dias_pendientes) + " días")
        except Exception as e:
            warn("SaldoVacacional: " + str(e))
            traceback.print_exc()

    # ------------------------------------------------------------------ #
    # 13. PRÉSTAMOS DE PRUEBA                                              #
    # ------------------------------------------------------------------ #
    def _prestamos(self, activos):
        step(13, "Prestamos de prueba...")
        try:
            from prestamos.models import Prestamo, TipoPrestamo, CuotaPrestamo
            tipo_personal = TipoPrestamo.objects.filter(nombre__icontains="Personal").first()
            tipo_adelanto = TipoPrestamo.objects.filter(nombre__icontains="Sueldo").first()
            if not tipo_personal and not tipo_adelanto:
                warn("Sin TipoPrestamo configurado — omitiendo préstamos")
                return

            # 2 préstamos de muestra
            staff = [p for p in activos if p.grupo_tareo == "STAFF"]
            if len(staff) < 2:
                return

            datos = [
                # (empleado_idx, tipo, monto, cuotas, estado)
                (0, tipo_personal, Decimal("3000"), 6, "EN_CURSO"),
                (1, tipo_adelanto, Decimal("1500"), 3, "EN_CURSO"),
            ]

            for idx, tipo, monto, cuotas, estado in datos:
                if idx >= len(staff) or not tipo:
                    continue
                p = staff[idx]
                cuota_m = (monto / cuotas).quantize(Decimal("0.01"))
                prest, c = Prestamo.objects.get_or_create(
                    personal=p,
                    tipo=tipo,
                    fecha_solicitud=datetime.date(2026, 1, 15),
                    defaults={
                        "monto_solicitado":  monto,
                        "monto_aprobado":    monto,
                        "num_cuotas":        cuotas,
                        "cuota_mensual":     cuota_m,
                        "tasa_interes":      Decimal("0"),
                        "fecha_aprobacion":  datetime.date(2026, 1, 20),
                        "estado":            estado,
                    },
                )
                if c:
                    # Crear cuotas
                    for i in range(cuotas):
                        mes_cuota = 2 + i
                        anio_cuota = 2026
                        if mes_cuota > 12:
                            mes_cuota -= 12
                            anio_cuota = 2027
                        try:
                            CuotaPrestamo.objects.get_or_create(
                                prestamo=prest,
                                numero_cuota=i + 1,
                                defaults={
                                    "monto_cuota":  cuota_m,
                                    "fecha_vencimiento": datetime.date(anio_cuota, mes_cuota, 28),
                                    "estado": "PAGADA" if i < 1 else "PENDIENTE",
                                },
                            )
                        except Exception:
                            pass
                ok(("  Creado" if c else "  Existe") + ": " + p.apellidos_nombres + " S/ " + str(monto) + " x" + str(cuotas))
        except Exception as e:
            warn("Prestamos: " + str(e))
            traceback.print_exc()
