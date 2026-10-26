from odoo import SUPERUSER_ID, api

CALENDARS = ("payroll_arg.resource_calendar_jornal_44h", "payroll_arg.resource_calendar_mensual_40h")


def migrate(cr, version):
    """Quita de los calendarios del módulo las 15 asistencias por defecto que Odoo agregó
    al crearlos (duplicaban la jornada: 16,8 hs/día en lugar de 8,8)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    own_ids = set(env["ir.model.data"].search([
        ("module", "=", "payroll_arg"),
        ("model", "=", "resource.calendar.attendance"),
    ]).mapped("res_id"))
    for xmlid in CALENDARS:
        cal = env.ref(xmlid, raise_if_not_found=False)
        if cal:
            cal.attendance_ids.filtered(lambda a: a.id not in own_ids).unlink()
