"""@file
Generación de recibos de un lote (asistente *Generar nóminas* de `payroll`): antes de crear nada, avisa
qué empleados no tienen contrato en el período y dónde se carga.
"""
from odoo import models
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    """Asistente de `payroll` que genera los recibos de los empleados elegidos para el lote activo."""

    _inherit = "hr.payslip.employees"

    def compute_sheet(self):
        """Genera y calcula los recibos, si todos los empleados tienen contrato en el período del lote.

        Sin esta verificación, un solo empleado sin contrato frena el lote entero a mitad de camino (el
        cálculo falla con recibos ya creados) y el mensaje no dice dónde se corrige.

        @return Resultado del asistente de `payroll`.
        @throws UserError Con la lista de empleados sin contrato y cómo cargarlo.
        """
        lote = self.env["hr.payslip.run"].browse(self.env.context.get("active_id"))
        if lote:
            sin_contrato = self.employee_ids.filtered(
                lambda e: not e._get_contracts(date_start=lote.date_start, date_end=lote.date_end).get(e.id))
            if sin_contrato:
                raise UserError(
                    f"Estos empleados no tienen contrato vigente entre el {lote.date_start:%d/%m/%Y} y el "
                    f"{lote.date_end:%d/%m/%Y}: {', '.join(sin_contrato.mapped('name'))}.\n\n"
                    "Cargar la Fecha de inicio del contrato en Empleados › (empleado) › pestaña Nómina, o "
                    "sacarlos de la selección."
                )
        return super().compute_sheet()
