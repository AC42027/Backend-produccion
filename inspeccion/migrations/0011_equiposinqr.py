from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspeccion', '0010_inspeccion_sap_nr_numero_inspeccion_sap_nr_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipoSinQR',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('equipo_nombre', models.CharField(max_length=255)),
                ('usuario', models.CharField(max_length=100)),
                ('usuario_nombre', models.CharField(max_length=255)),
                ('fecha', models.DateField()),
                ('hora', models.TimeField()),
                ('comentario', models.TextField(blank=True, null=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-creado_en'],
                'verbose_name': 'Equipo sin QR',
                'verbose_name_plural': 'Equipos sin QR',
            },
        ),
    ]