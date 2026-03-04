"""Carga tipos de permiso estándar para legislación peruana."""
from django.core.management.base import BaseCommand
from vacaciones.models import TipoPermiso


TIPOS = [
    # ── Régimen de Turno (Foráneos) ───────────────────────────────────────────
    # Aplica solo si mod_roster=True. Al aprobarse, crea entrada Roster(DL).
    {'nombre': 'Bajada / Día Libre (Régimen)', 'codigo': 'bajada-dl',
     'dias_max': 0, 'pagado': True, 'requiere_sustento': False,
     'base_legal': 'DL 713 Art. 24 / Régimen acumulativo 14x7, 21x7, etc.',
     'descripcion': (
         'Día libre ganado por trabajar el régimen completo de turnos. '
         'Solo aplica a personal foráneo con régimen acumulativo (14x7, 21x7, 28x14). '
         'Al aprobarse, crea automáticamente una entrada de Roster con código DL.'
     ), 'orden': 1},
    {'nombre': 'Bajada Acumulada (Saldo 2025)', 'codigo': 'bajada-dla',
     'dias_max': 0, 'pagado': True, 'requiere_sustento': False,
     'base_legal': 'DL 713 / Saldo acumulado al 31/12/2025',
     'descripcion': (
         'Día libre del saldo acumulado al corte de 31/12/2025. '
         'Al aprobarse, crea automáticamente una entrada de Roster con código DLA. '
         'Máximo 7 días consecutivos.'
     ), 'orden': 2},
    # ── Permisos Legales (Legislación Peruana) ────────────────────────────────
    {'nombre': 'Licencia por Paternidad', 'codigo': 'paternidad', 'dias_max': 10, 'pagado': True, 'requiere_sustento': True, 'base_legal': 'Ley 29409 (10 días consecutivos)'},
    {'nombre': 'Licencia por Maternidad', 'codigo': 'maternidad', 'dias_max': 98, 'pagado': True, 'requiere_sustento': True, 'base_legal': 'Ley 26644 (98 días, 49 pre + 49 post parto)'},
    {'nombre': 'Licencia por Fallecimiento Familiar', 'codigo': 'fallecimiento', 'dias_max': 5, 'pagado': True, 'requiere_sustento': True, 'base_legal': 'Ley 30012 (padres, cónyuge, hijos)'},
    {'nombre': 'Licencia por Matrimonio', 'codigo': 'matrimonio', 'dias_max': 3, 'pagado': False, 'requiere_sustento': True, 'base_legal': 'Convenio colectivo (no regulado por ley)'},
    {'nombre': 'Permiso por Citación Judicial', 'codigo': 'citacion-judicial', 'dias_max': 0, 'pagado': True, 'requiere_sustento': True, 'base_legal': 'DS 003-97-TR Art. 32'},
    {'nombre': 'Licencia por Enfermedad Grave Familiar', 'codigo': 'enfermedad-familiar', 'dias_max': 7, 'pagado': True, 'requiere_sustento': True, 'base_legal': 'Ley 30012 (familiar directo en estado grave/terminal)'},
    {'nombre': 'Licencia Sindical', 'codigo': 'sindical', 'dias_max': 30, 'pagado': True, 'requiere_sustento': False, 'base_legal': 'DS 010-2003-TR (dirigentes sindicales)'},
    {'nombre': 'Permiso por Lactancia', 'codigo': 'lactancia', 'dias_max': 0, 'pagado': True, 'requiere_sustento': False, 'base_legal': 'Ley 27240 (1 hora diaria hasta 1 año del hijo)'},
    {'nombre': 'Licencia sin Goce', 'codigo': 'sin-goce', 'dias_max': 0, 'pagado': False, 'requiere_sustento': False, 'base_legal': 'Acuerdo entre partes'},
    {'nombre': 'Permiso Personal', 'codigo': 'personal', 'dias_max': 0, 'pagado': False, 'requiere_sustento': False, 'base_legal': 'Política interna', 'descuenta_vacaciones': True},
    {'nombre': 'Descanso Médico', 'codigo': 'descanso-medico', 'dias_max': 0, 'pagado': True, 'requiere_sustento': True, 'base_legal': 'DS 009-97-SA (ESSALUD subsidio desde día 21)'},
    {'nombre': 'Licencia por Adopción', 'codigo': 'adopcion', 'dias_max': 30, 'pagado': True, 'requiere_sustento': True, 'base_legal': 'Ley 27409 (30 días post resolución)'},
]


class Command(BaseCommand):
    help = 'Carga tipos de permiso estándar (legislación peruana)'

    def handle(self, *args, **options):
        creados = 0
        for data in TIPOS:
            desc_vac = data.pop('descuenta_vacaciones', False)
            _, created = TipoPermiso.objects.get_or_create(
                codigo=data['codigo'],
                defaults={**data, 'descuenta_vacaciones': desc_vac},
            )
            if created:
                creados += 1
        self.stdout.write(self.style.SUCCESS(f'{creados} tipos de permiso creados.'))
