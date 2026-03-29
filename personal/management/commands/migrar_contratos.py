"""
Comando para migrar datos de contrato de Personal a registros Contrato.
Crea un objeto Contrato VIGENTE por cada Personal activo que tenga
datos de contrato (tipo_contrato, fecha_inicio_contrato).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from personal.models import Personal, Contrato


class Command(BaseCommand):
    help = 'Migra datos de contrato de Personal a registros Contrato'

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        creados = 0
        omitidos = 0
        ya_existentes = 0

        personales = Personal.objects.filter(estado='Activo').select_related('subarea__area')

        for p in personales:
            # Si ya tiene un contrato registrado, omitir
            if Contrato.objects.filter(personal=p).exists():
                ya_existentes += 1
                continue

            # Necesita al menos fecha de inicio para crear contrato
            if not p.fecha_inicio_contrato and not p.tipo_contrato:
                omitidos += 1
                continue

            # Determinar estado
            if p.tipo_contrato == 'INDEFINIDO':
                estado = 'VIGENTE'
            elif p.fecha_fin_contrato and p.fecha_fin_contrato < hoy:
                estado = 'VENCIDO'
            else:
                estado = 'VIGENTE'

            Contrato.objects.create(
                personal=p,
                tipo_contrato=p.tipo_contrato or 'PLAZO_FIJO',
                fecha_inicio=p.fecha_inicio_contrato or p.fecha_alta or hoy,
                fecha_fin=p.fecha_fin_contrato,
                cargo_contrato=p.cargo or '',
                sueldo_pactado=p.sueldo_base,
                estado=estado,
                observaciones='Migrado automaticamente desde datos de Personal',
            )
            creados += 1

        self.stdout.write(
            f'Contratos creados: {creados}, '
            f'omitidos (sin datos): {omitidos}, '
            f'ya existentes: {ya_existentes}'
        )
