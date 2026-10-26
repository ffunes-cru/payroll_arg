from odoo import fields, models


class HrPayslipInput(models.Model):
    """Línea de entrada = única fuente de las novedades del recibo.

    ``employee_id`` y ``payslip_run_id`` se almacenan para poder editar todas las
    entradas del lote en una sola matriz (empleado × código).
    """

    _inherit = "hr.payslip.input"

    contract_id = fields.Many2one(
        "hr.version",
        string="Contract",
        required=False,
    )
    employee_id = fields.Many2one(
        related="payslip_id.employee_id", store=True, index=True, string="Empleado"
    )
    payslip_run_id = fields.Many2one(
        related="payslip_id.payslip_run_id", store=True, index=True, string="Lote"
    )
    payslip_state = fields.Selection(related="payslip_id.state", string="Estado del Recibo")
