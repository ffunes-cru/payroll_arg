"""@file
Novedades fijadas para todo un lote (`hr.payslip.run.novelty`): un mismo valor para todos los recibos
(precio de la vianda, monto de presentismo, asignación no remunerativa del acuerdo…).
"""
from odoo import api, fields, models


class HrPayslipRunNovelty(models.Model):
    """Valor de una novedad fijado para todo el lote (por ejemplo monto de Presentismo, precio
    de la vianda, horas de feriado). Se carga en los recibos al generarlos y con
    "Aplicar"; mientras exista, "Recargar novedades del período" no pisa ese código.
    """

    _name = "hr.payslip.run.novelty"
    _description = "Novedad fijada en el lote de liquidación"
    _order = "run_id, id"

    run_id = fields.Many2one("hr.payslip.run", required=True, ondelete="cascade", index=True)
    input_id = fields.Many2one(
        "hr.rule.input",
        string="Novedad",
        required=True,
        ondelete="restrict",
    )
    code = fields.Char(related="input_id.code", store=True)
    amount = fields.Float(string="Valor", digits=(16, 2))

    _run_code_uniq = models.Constraint(
        "UNIQUE(run_id, code)",
        "Cada novedad puede fijarse una sola vez por lote.",
    )

    @api.depends("input_id", "amount")
    def _compute_display_name(self):
        """Nombre "Novedad: valor"."""
        for novelty in self:
            novelty.display_name = f"{novelty.input_id.name}: {novelty.amount:,.2f}"

    def action_apply(self):
        """Pisa el código en todos los recibos editables del lote.

        Botón *Aplicar a todos* de la línea. También pisa lo que se haya corregido a mano en un recibo.

        @return True.
        """
        for novelty in self:
            slips = novelty.run_id.slip_ids.filtered(lambda s: s.state in ("draft", "verify"))
            slips._set_input_amounts({novelty.code: novelty.amount})
        return True
