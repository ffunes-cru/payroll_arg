"""@file
Calendario de trabajo (`resource.calendar`). Sin cambios propios: el módulo trae los calendarios
"Jornal Fábrica UOM (44 hs)" y "Administración / Mensual (40 hs)" en data/afip_data.xml.
"""
from odoo import models


class ResourceCalendar(models.Model):
    """Punto de extensión del calendario (vacío)."""

    _inherit = "resource.calendar"
