"""
Agrega índice parcial compuesto para acelerar _qs_staff_dedup (DISTINCT ON).

Nota: CONCURRENTLY solo aplica en PostgreSQL. En SQLite (desarrollo local)
se usa CREATE INDEX IF NOT EXISTS sin CONCURRENTLY.
"""
from django.db import migrations, connection


def _create_index(apps, schema_editor):
    db_engine = schema_editor.connection.vendor
    if db_engine == 'postgresql':
        schema_editor.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS
                tareo_staff_dedup_idx
            ON tareo_registrotareo (personal_id, fecha, importacion_id DESC)
            WHERE grupo = 'STAFF' AND personal_id IS NOT NULL;
        """)
    elif db_engine == 'sqlite':
        schema_editor.execute("""
            CREATE INDEX IF NOT EXISTS
                tareo_staff_dedup_idx
            ON tareo_registrotareo (personal_id, fecha, importacion_id DESC);
        """)
    # Otros backends: skip


def _drop_index(apps, schema_editor):
    db_engine = schema_editor.connection.vendor
    if db_engine == 'postgresql':
        schema_editor.execute("DROP INDEX IF EXISTS tareo_staff_dedup_idx;")
    elif db_engine == 'sqlite':
        schema_editor.execute("DROP INDEX IF EXISTS tareo_staff_dedup_idx;")


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('tareo', '0031_add_anthropic_provider'),
    ]

    operations = [
        migrations.RunPython(_create_index, _drop_index),
    ]
