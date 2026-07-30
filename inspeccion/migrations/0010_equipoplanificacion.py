# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspeccion', '0009_inspeccion_comentario_hallazgo_inspeccion_sap_equnr_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipoPlanificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombres', models.TextField(blank=True, default='', help_text='Lista de nombres del equipo, separados por salto de linea')),
            ],
            options={
                'verbose_name': 'Equipo de Planificacion',
                'verbose_name_plural': 'Equipo de Planificacion',
            },
        ),
    ]
