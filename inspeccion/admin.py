from django.contrib import admin
from .models import (
    Division, Area, Zona, Equipo, Inspeccion, UbicacionFisica,
    Categoria, InspeccionTecnico, PreguntaTecnica, Owner
)

# ---------- EQUIPOS ----------
@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = (
        "id", "nombre",
        "division_nombre", "area_nombre", "zona_nombre",
        "owner_nombre", "categoria_nombre", "ubicacion_descripcion",
    )
    list_filter = (
        ("division", admin.RelatedOnlyFieldListFilter),
        ("area", admin.RelatedOnlyFieldListFilter),
        ("zona", admin.RelatedOnlyFieldListFilter),
        ("owner", admin.RelatedOnlyFieldListFilter),
        ("categoria", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "nombre",
        "division__nombre", "area__nombre", "zona__nombre",
        "owner__nombre", "categoria__nombre",
        "ubicacion__descripcion",
    )
    list_select_related = ("division", "area", "zona", "owner", "categoria", "ubicacion")
    ordering = ("division__nombre", "area__nombre", "zona__nombre", "nombre")
    autocomplete_fields = ("division", "area", "zona", "owner", "categoria", "ubicacion")

    # columnas legibles
    def division_nombre(self, obj): return getattr(obj.division, "nombre", "")
    division_nombre.short_description = "División"
    division_nombre.admin_order_field = "division__nombre"

    def area_nombre(self, obj): return getattr(obj.area, "nombre", "")
    area_nombre.short_description = "Área"
    area_nombre.admin_order_field = "area__nombre"

    def zona_nombre(self, obj): return getattr(obj.zona, "nombre", "")
    zona_nombre.short_description = "Zona"
    zona_nombre.admin_order_field = "zona__nombre"

    def owner_nombre(self, obj): return getattr(obj.owner, "nombre", "")
    owner_nombre.short_description = "Owner"
    owner_nombre.admin_order_field = "owner__nombre"

    def categoria_nombre(self, obj): return getattr(obj.categoria, "nombre", "")
    categoria_nombre.short_description = "Categoría"
    categoria_nombre.admin_order_field = "categoria__nombre"

    def ubicacion_descripcion(self, obj): return getattr(obj.ubicacion, "descripcion", "")
    ubicacion_descripcion.short_description = "Ubicación física"
    ubicacion_descripcion.admin_order_field = "ubicacion__descripcion"


# ---------- RESTO (opcional, más útil con filtros/búsqueda) ----------
@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    ordering = ("nombre",)

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "division")
    list_filter = (("division", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("nombre", "division__nombre")
    list_select_related = ("division",)
    ordering = ("division__nombre", "nombre")

@admin.register(Zona)
class ZonaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "area")
    list_filter = (("area", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("nombre", "area__nombre")
    list_select_related = ("area",)
    ordering = ("area__nombre", "nombre")

@admin.register(UbicacionFisica)
class UbicacionFisicaAdmin(admin.ModelAdmin):
    list_display = ("id", "descripcion")
    search_fields = ("descripcion",)
    ordering = ("descripcion",)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    ordering = ("nombre",)

@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
    ordering = ("nombre",)

@admin.register(Inspeccion)
class InspeccionAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'equipo', 'sap_equnr', 'sap_puesto_trabajo', 'owner')
    list_filter = ("fecha", ("equipo", admin.RelatedOnlyFieldListFilter))
    search_fields = ("equipo__nombre", "sap_equnr", "sap_puesto_trabajo")
    fields = (
        'fecha', 'hora_inicio', 'hora_fin', 
        'division', 'area', 'zona', 'equipo', 
        'sap_equnr', 'sap_equnr_desc', 'sap_tplnr', 'sap_puesto_trabajo', # Nuevos campos
        'observaciones', 'comentario_hallazgo', # Comentario de SAP
        'owner'
    )

@admin.register(InspeccionTecnico)
class InspeccionTecnicoAdmin(admin.ModelAdmin):
    list_display = ("id", "inspeccion", "descripcion", "estado")
    list_filter = ("estado",)

@admin.register(PreguntaTecnica)
class PreguntaTecnicaAdmin(admin.ModelAdmin):
    list_display = ("id", "descripcion", "categoria")
    list_filter = (("categoria", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("descripcion", "categoria__nombre")
