from odoo import api, fields, models


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    tipo_concepto = fields.Selection(
        [
            ("1", "Remunerativo"),
            ("2", "No Remunerativo"),
            ("3", "Retención / Descuento"),
            ("4", "Contribución Patronal / Totalizador"),
        ],
        string="Tipo de Concepto AFIP",
        default=False,
        help="1: Remunerativo, 2: No Remunerativo, 3: Retención / Descuento, 4: Contribución Patronal / Totalizador",
    )
    afip_code = fields.Char(
        string="Código Concepto AFIP LSD",
        size=10,
        help="Código del concepto del empleador registrado en el Libro de Sueldos Digital (hasta 10 caracteres)",
    )
    afip_unit = fields.Selection(
        [
            ("H", "Horas"),
            ("D", "Días"),
            ("%", "Porcentaje"),
            ("$", "Moneda / Importe"),
            ("U", "Unidades"),
            (" ", "Sin Unidad (En Blanco)"),
        ],
        string="Unidad de Medida AFIP",
        default="D",
        help="Unidad de medida para el Registro 3 del Libro de Sueldos Digital (H=horas, D=días)",
    )

    @api.onchange("tipo_concepto")
    def _onchange_tipo_concepto(self):
        mapping = {
            "1": "payroll_arg.cat_rem",
            "2": "payroll_arg.cat_norem",
            "3": "payroll_arg.cat_ret",
            "4": "payroll_arg.cat_comp",
        }
        if self.tipo_concepto in mapping:
            cat = self.env.ref(mapping[self.tipo_concepto], raise_if_not_found=False)
            if cat:
                self.category_id = cat

    @api.onchange("category_id")
    def _onchange_category_id(self):
        if self.category_id and not self.tipo_concepto:
            code = (self.category_id.code or "").upper()
            mapping = {
                "REM": "1",
                "BASIC": "1",
                "ALW": "1",
                "NOREM": "2",
                "DED": "3",
                "RET": "3",
                "COMP": "4",
            }
            if code in mapping:
                self.tipo_concepto = mapping[code]
