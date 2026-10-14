from odoo import api, fields, models


class HrGananciasScale(models.Model):
    _name = "hr.ganancias.scale"
    _description = "Escala Progresiva Impuesto a las Ganancias (Art. 94 LIG)"
    _order = "date_from desc, sequence, id"

    name = fields.Char(string="Nombre / Período", required=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    date_from = fields.Date(string="Vigencia Desde", required=True)
    date_to = fields.Date(string="Vigencia Hasta", required=True)
    active = fields.Boolean(string="Activo", default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="company_id.currency_id",
        readonly=True,
    )

    line_ids = fields.One2many(
        "hr.ganancias.scale.line",
        "scale_id",
        string="Tramos de la Escala",
        copy=True,
    )

    # Deducciones personales (Art. 30 LIG) — Valores anuales de referencia
    deduccion_ganancia_no_imponible = fields.Float(
        string="Ganancia No Imponible (Anual)",
        help="Monto anual de Ganancia No Imponible (Art. 30 inc. a).",
    )
    deduccion_especial = fields.Float(
        string="Deducción Especial (Anual)",
        help="Deducción especial anual de 4ta categoría (Art. 30 inc. c).",
    )
    deduccion_conyuge = fields.Float(
        string="Carga Cónyuge (Anual)",
        help="Deducción anual por cónyuge o unión convivencial.",
    )
    deduccion_hijo = fields.Float(
        string="Carga por Hijo (Anual)",
        help="Deducción anual por cada hijo/hijastro menor de 18 años.",
    )
    deduccion_hijo_incapacitado = fields.Float(
        string="Hijo Discapacitado (Anual)",
        help="Deducción anual por cada hijo incapacitado para el trabajo.",
    )

    @api.model
    def get_scale_for_date(self, target_date):
        """Busca la escala activa vigente para la fecha indicada."""
        return self.search(
            [
                ("date_from", "<=", target_date),
                ("date_to", ">=", target_date),
                ("active", "=", True),
            ],
            limit=1,
        )

    def calculate_annual_bracket(self, net_taxable_accumulated, month):
        """Calcula el impuesto acumulado aplicando la escala Art. 94 proporcional al mes M (1 a 12).
        
        Según RG 4003, los tramos de la escala se multiplican por (month / 12.0)
        para determinar la alícuota acumulada correspondiente al período.
        """
        self.ensure_one()
        if net_taxable_accumulated <= 0:
            return 0.0

        month_factor = min(max(month, 1), 12) / 12.0

        for line in self.line_ids.sorted(key=lambda l: l.amount_from):
            bracket_from = line.amount_from * month_factor
            bracket_to = line.amount_to * month_factor if line.amount_to > 0 else float("inf")
            fixed_amt = line.fixed_amount * month_factor
            rate_pct = line.rate / 100.0

            if bracket_from <= net_taxable_accumulated < bracket_to or bracket_to == float("inf"):
                excess = net_taxable_accumulated - bracket_from
                tax = fixed_amt + (excess * rate_pct)
                return round(tax, 2)

        return 0.0


class HrGananciasScaleLine(models.Model):
    _name = "hr.ganancias.scale.line"
    _description = "Tramo de Escala Progresiva Ganancias"
    _order = "amount_from"

    scale_id = fields.Many2one(
        "hr.ganancias.scale",
        string="Escala",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Secuencia", default=10)
    amount_from = fields.Float(string="Desde ($ Anual)", required=True)
    amount_to = fields.Float(string="Hasta ($ Anual)", required=True, default=0.0)
    fixed_amount = fields.Float(string="Cuota Fija ($ Anual)", default=0.0)
    rate = fields.Float(string="Alícuota Sobre Excedente (%)", required=True)


class HrGananciasAccumulator(models.Model):
    _name = "hr.ganancias.accumulator"
    _description = "Acumulador Mensual Ganancias 4ta Categoría"
    _order = "employee_id, year desc, month desc"
    _rec_name = "display_name"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        required=True,
        ondelete="cascade",
        index=True,
    )
    year = fields.Integer(string="Año Fiscal", required=True, index=True)
    month = fields.Integer(string="Mes (1-12)", required=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="employee_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="company_id.currency_id",
        readonly=True,
    )

    # Valores del mes
    gross_rem = fields.Float(string="Bruto Remunerativo Mes ($)")
    deductions_employee = fields.Float(string="Aportes Trabajador Mes ($)")
    other_deductions = fields.Float(string="Otras Deducciones Mes (SIRADIG) ($)")

    # Acumulados
    accumulated_gross = fields.Float(string="Bruto Acumulado ($)")
    accumulated_deductions = fields.Float(string="Aportes Ley Acumulados ($)")
    personal_deductions = fields.Float(string="Deducciones Personales Acumuladas ($)")
    accumulated_net_taxable = fields.Float(string="Ganancia Neta Sujeta a Impuesto ($)")
    accumulated_tax = fields.Float(string="Impuesto Acumulado Determinado ($)")
    accumulated_retained = fields.Float(string="Retenciones Anteriores Acumuladas ($)")

    # Retención resultante
    retention_calculated = fields.Float(string="Retención Calculada Mes ($)")
    retention_applied = fields.Float(string="Retención Efectiva Mes ($)")

    payslip_id = fields.Many2one("hr.payslip", string="Liquidación", ondelete="set null")
    display_name = fields.Char(string="Descripción", compute="_compute_display_name")
    notes = fields.Text(string="Notas")

    @api.depends("employee_id", "year", "month")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or f"Emp {rec.employee_id.id}"
            rec.display_name = f"{emp} - {rec.year}/{rec.month:02d}"
