from odoo import fields, models


class AfipCct(models.Model):
    _name = "afip.cct"
    _description = "Convenio Colectivo de Trabajo (CCT)"

    code = fields.Char(string="Código CCT", required=True)
    name = fields.Char(string="Nombre Convenio", required=True)
    description = fields.Text(string="Descripción")
    union_rate = fields.Float(string="Porcentaje Aporte Sindical (%)", default=2.0)
    vacation_divisor = fields.Float(
        string="Divisor Vacaciones (Art. 155 LCT)",
        default=25.0,
        help="Divisor para el cálculo de vacaciones. LCT Art. 155: 25 (sueldo / 25 × días). "
             "Algunos CCT establecen un divisor diferente (ej: 30).",
    )


class AfipLaborCategory(models.Model):
    _name = "afip.labor.category"
    _description = "Categoría Profesional de Convenio"

    name = fields.Char(string="Nombre Categoría", required=True)
    code = fields.Char(string="Código Categoría", required=True)
    cct_id = fields.Many2one("afip.cct", string="Convenio Colectivo")
    category_type = fields.Selection(
        [
            ("monthly", "Mensualizado"),
            ("hourly", "Jornalizado"),
        ],
        string="Tipo de Categoría",
        default="monthly",
        required=True,
    )
    hourly_wage = fields.Float(string="Valor Hora Básico", default=0.0)
    monthly_wage = fields.Float(string="Sueldo Básico Mensual", default=0.0)

    def action_update_contract_wages(self):
        """Actualiza el sueldo básico de todos los contratos activos asociados a esta categoría."""
        self.ensure_one()
        contracts = self.env["hr.version"].search([("labor_category_id", "=", self.id)])
        new_wage = self.hourly_wage if self.category_type == "hourly" else self.monthly_wage
        if new_wage > 0:
            contracts.write({"wage": new_wage})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Sueldos Actualizados",
                "message": f"Se actualizó el sueldo a {len(contracts)} contrato(s) con la categoría {self.name}.",
                "sticky": False,
                "type": "success",
            },
        }


class AfipHealthInsurance(models.Model):
    _name = "afip.health.insurance"
    _description = "Obra Social (Registro Nacional de Obras Sociales - RNOS)"

    code = fields.Char(string="Código RNOS", size=6, required=True, index=True)
    name = fields.Char(string="Nombre Obra Social", required=True)
    initials = fields.Char(string="Siglas / Abreviatura")
    active = fields.Boolean(default=True)

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, f"[{rec.code}] {rec.name}"))
        return result


class AfipContractType(models.Model):
    _name = "afip.contract.type"
    _description = "Modalidad de Contratación AFIP"

    code = fields.Char(string="Código AFIP", size=3, required=True, index=True)
    name = fields.Char(string="Descripción", required=True)


class AfipSituation(models.Model):
    _name = "afip.situation"
    _description = "Situación de Revista AFIP"

    code = fields.Char(string="Código AFIP", size=2, required=True, index=True)
    name = fields.Char(string="Descripción", required=True)


class AfipCondition(models.Model):
    _name = "afip.condition"
    _description = "Condición del Trabajador AFIP"

    code = fields.Char(string="Código AFIP", size=2, required=True, index=True)
    name = fields.Char(string="Descripción", required=True)


class AfipActivity(models.Model):
    _name = "afip.activity"
    _description = "Actividad del Trabajador AFIP"

    code = fields.Char(string="Código AFIP", size=3, required=True, index=True)
    name = fields.Char(string="Descripción", required=True)


class AfipZone(models.Model):
    _name = "afip.zone"
    _description = "Zona Geográfica AFIP"

    code = fields.Char(string="Código AFIP", size=2, required=True, index=True)
    name = fields.Char(string="Descripción", required=True)


class AfipSiniestrado(models.Model):
    _name = "afip.siniestrado"
    _description = "Código de Siniestrado AFIP"

    code = fields.Char(string="Código AFIP", size=2, required=True, index=True)
    name = fields.Char(string="Descripción", required=True)
