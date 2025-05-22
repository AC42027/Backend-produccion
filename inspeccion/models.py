from django.db import models

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class PreguntaTecnica(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='preguntas')
    descripcion = models.TextField()

    def __str__(self):
        return self.descripcion

class UbicacionFisica(models.Model):
    descripcion = models.CharField(max_length=255)

    def __str__(self):
        return self.descripcion

class Division(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Area(models.Model):
    nombre = models.CharField(max_length=100)
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='areas')

    def __str__(self):
        return self.nombre

class Zona(models.Model):
    nombre = models.CharField(max_length=100)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='zonas')

    def __str__(self):
        return self.nombre

class Owner(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Equipo(models.Model):
    nombre = models.CharField(max_length=100)
    ubicacion = models.ForeignKey(UbicacionFisica, on_delete=models.SET_NULL, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    division = models.ForeignKey(Division, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    zona = models.ForeignKey(Zona, on_delete=models.SET_NULL, null=True, blank=True)
    owner = models.ForeignKey(Owner, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipos')

    def __str__(self):
        return self.nombre

class Inspeccion(models.Model):
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    division = models.ForeignKey(Division, on_delete=models.CASCADE)
    area = models.ForeignKey(Area, on_delete=models.CASCADE)
    zona = models.ForeignKey(Zona, on_delete=models.CASCADE)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"Inspección {self.id} - {self.fecha}"

class InspeccionTecnico(models.Model):
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE, related_name='revisiones')
    descripcion = models.TextField()
    estado = models.CharField(max_length=10, choices=[('OK', 'OK'), ('NOK', 'NOK'), ('NA', 'No Aplica')])

    def __str__(self):
        return f"{self.inspeccion.id} - {self.descripcion[:20]}"
