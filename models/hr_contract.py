import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Constantes de estructura salarial — SSOT para codes de estructura
HOURLY_STRUCT_CODES = (
    "JORNAL_QUINC_ARG",
    "VACACIONES_JORNAL_ARG",
    "SAC_JORNAL_ARG",
    "FINAL_JORNAL_ARG",
)
MONTHLY_STRUCT_CODES = (
    "MENSUAL_ARG",
    "VACACIONES_MENSUAL_ARG",
    "SAC_MENSUAL_ARG",
    "FINAL_MENSUAL_ARG",
)
HOURLY_SCHEDULE_PAYS = ("bi-weekly", "weekly")
MONTHLY_SCHEDULE_PAYS = ("monthly",)

# Constante legal argentina
DIAS_BASE_MENSUAL_LCT = 30


class HrContract(models.Model):
    _inherit = "hr.version"

    wage_type = fields.Selection(
        [
            ("monthly", "Mensualizado"),
            ("hourly", "Jornalizado (Valor Hora)"),
        ],
        string="Tipo de Salario",
        default="monthly",
        help="Mensual: sueldo fijo mensual. Jornalizado: el importe básico corresponde al valor por hora.",
    )
    cct_id = fields.Many2one("afip.cct", string="Convenio Colectivo")
    labor_category_id = fields.Many2one("afip.labor.category", string="Categoría Profesional")
    afip_contract_type_id = fields.Many2one("afip.contract.type", string="Modalidad Contratación AFIP")
    afip_situation_id = fields.Many2one("afip.situation", string="Situación de Revista AFIP")
    afip_condition_id = fields.Many2one("afip.condition", string="Condición AFIP")
    afip_activity_id = fields.Many2one("afip.activity", string="Actividad AFIP")
    afip_zone_id = fields.Many2one("afip.zone", string="Zona Geográfica AFIP")
    afip_siniestrado_id = fields.Many2one("afip.siniestrado", string="Código Siniestrado")
    is_convencionado = fields.Boolean(
        string="Convencionado",
        default=True,
        help="Indica si el empleado está bajo Convenio Colectivo de Trabajo (CCT). Si se desmarca (Fuera de Convenio), no liquida aportes sindicales ni adicionales por antigüedad de CCT.",
    )
    has_reduction = fields.Boolean(string="Corresponde Reducción Contribuciones", default=False)
    has_mandatory_life_insurance = fields.Boolean(string="Seguro de Vida Obligatorio", default=True)
    additional_ss_contrib_percent = fields.Float(string="Aporte Adicional Seg. Social (%)", default=0.0)
    diff_task_contrib_percent = fields.Float(string="Contribución Tarea Diferencial (%)", default=0.0)
    additional_health_insurance_amount = fields.Float(string="Importe Adicional Obra Social", default=0.0)
    aporte_adicional_ss_monto = fields.Float(
        string="Aporte Adicional Seg. Social ($)",
        related="employee_id.aporte_adicional_ss_monto",
        readonly=False,
        help="Monto fijo en pesos a descontar de la liquidación en la 2da quincena como Aporte Adicional de Seguridad Social.",
    )

    # ──────────────────────────────────────────────
    # CONSTRAINS — Impiden estados inconsistentes
    # ──────────────────────────────────────────────

    @api.constrains("wage_type", "struct_id")
    def _check_wage_type_vs_struct(self):
        """Un jornal NUNCA puede tener estructura mensual, y viceversa.

        Los onchange sincronizan en la UI, pero esta validación protege contra
        escrituras por API, imports, y operaciones batch.
        """
        for rec in self:
            if not rec.struct_id:
                continue
            code = rec.struct_id.code
            emp_name = rec.employee_id.name or rec.name or "el empleado"
            if rec.wage_type == "hourly" and code in MONTHLY_STRUCT_CODES:
                raise ValidationError(
                    f"El contrato de '{emp_name}' es Jornalizado pero tiene "
                    f"asignada la estructura mensual '{rec.struct_id.name}'. "
                    f"Corrija el tipo de salario o la estructura salarial."
                )
            if rec.wage_type == "monthly" and code in HOURLY_STRUCT_CODES:
                raise ValidationError(
                    f"El contrato de '{emp_name}' es Mensualizado pero tiene "
                    f"asignada la estructura de jornales '{rec.struct_id.name}'. "
                    f"Corrija el tipo de salario o la estructura salarial."
                )

    @api.constrains("wage_type", "schedule_pay")
    def _check_wage_type_vs_schedule_pay(self):
        """Validación de periodicidad relajada para no bloquear la operación."""
        pass

    @api.constrains("labor_category_id", "wage_type")
    def _check_labor_category_vs_wage_type(self):
        """La categoría laboral debe coincidir con el tipo de salario."""
        for rec in self:
            if rec.labor_category_id and rec.labor_category_id.category_type:
                if rec.labor_category_id.category_type != rec.wage_type:
                    emp_name = rec.employee_id.name or rec.name or "el empleado"
                    raise ValidationError(
                        f"La categoría '{rec.labor_category_id.name}' es de tipo "
                        f"'{rec.labor_category_id.category_type}' pero el contrato de "
                        f"'{emp_name}' es '{rec.wage_type}'. "
                        f"Cambie la categoría o el tipo de salario."
                    )

    # ──────────────────────────────────────────────
    # HELPERS CENTRALIZADOS
    # ──────────────────────────────────────────────

    @api.model
    def _get_default_calendar(self, wage_type):
        """Resuelve el calendario por defecto para un wage_type dado.

        Cascada:
        1. env.ref del XML data (resource_calendar_jornal_44h / resource_calendar_mensual_40h)
        2. Búsqueda por horas semanales (44h para jornal, 40h para mensual)
        3. False con WARNING en log

        Returns: record de resource.calendar o False
        """
        if wage_type == "hourly":
            cal = self.env.ref("payroll_arg.resource_calendar_jornal_44h", raise_if_not_found=False)
            if not cal:
                cal = self.env["resource.calendar"].search(
                    [("hours_per_week", "=", 44)], limit=1
                )
            if not cal:
                _logger.warning(
                    "No se encontró calendario de trabajo para jornalizados (44h). "
                    "Cree uno con XML ID 'payroll_arg.resource_calendar_jornal_44h'."
                )
            return cal
        else:
            cal = self.env.ref("payroll_arg.resource_calendar_mensual_40h", raise_if_not_found=False)
            if not cal:
                cal = self.env["resource.calendar"].search(
                    [("hours_per_week", "in", [40, 48])], limit=1
                )
            if not cal:
                _logger.warning(
                    "No se encontró calendario de trabajo para mensualizados (40h). "
                    "Cree uno con XML ID 'payroll_arg.resource_calendar_mensual_40h'."
                )
            return cal

    @api.model
    def _get_default_struct(self, wage_type, tipo_liquidacion=None):
        """Resuelve la estructura salarial por defecto para un wage_type y tipo_liquidacion dado.

        Args:
            wage_type (str): 'hourly' o 'monthly'
            tipo_liquidacion (str, optional): 'Vacaciones', 'SAC', 'Liquidación Final', 'Mensual', etc.

        Returns: record de hr.payroll.structure o False
        """
        if wage_type == "hourly":
            if tipo_liquidacion == "Vacaciones":
                code = "VACACIONES_JORNAL_ARG"
            elif tipo_liquidacion == "SAC":
                code = "SAC_JORNAL_ARG"
            elif tipo_liquidacion == "Liquidación Final":
                code = "FINAL_JORNAL_ARG"
            else:
                code = "JORNAL_QUINC_ARG"
        else:
            if tipo_liquidacion == "Vacaciones":
                code = "VACACIONES_MENSUAL_ARG"
            elif tipo_liquidacion == "SAC":
                code = "SAC_MENSUAL_ARG"
            elif tipo_liquidacion == "Liquidación Final":
                code = "FINAL_MENSUAL_ARG"
            else:
                code = "MENSUAL_ARG"

        struct = self.env["hr.payroll.structure"].search([("code", "=", code)], limit=1)
        if not struct:
            base_code = "JORNAL_QUINC_ARG" if wage_type == "hourly" else "MENSUAL_ARG"
            struct = self.env["hr.payroll.structure"].search([("code", "=", base_code)], limit=1)
            if not struct:
                _logger.warning("No se encontró estructura salarial con código '%s' ni '%s'.", code, base_code)
        return struct

    # ──────────────────────────────────────────────
    # ONCHANGES
    # ──────────────────────────────────────────────

    @api.onchange("resource_calendar_id")
    def _onchange_resource_calendar(self):
        if self.resource_calendar_id:
            cal = self.resource_calendar_id
            name = (cal.name or "").lower()
            if "jornal" in name or "fábrica" in name or "fabrica" in name or cal.hours_per_week == 44:
                self.wage_type = "hourly"
                self.schedule_pay = "bi-weekly"
                struct = self._get_default_struct("hourly")
                if struct:
                    self.struct_id = struct
            elif "mensual" in name or "admin" in name or cal.hours_per_week in (40, 48):
                self.wage_type = "monthly"
                self.schedule_pay = "monthly"
                struct = self._get_default_struct("monthly")
                if struct:
                    self.struct_id = struct

    @api.onchange("wage_type")
    def _onchange_wage_type(self):
        if self.wage_type == "hourly":
            self.schedule_pay = "bi-weekly"
            struct = self._get_default_struct("hourly")
            if struct:
                self.struct_id = struct
            cal_hourly = self._get_default_calendar("hourly")
            cal_monthly = self._get_default_calendar("monthly")
            if cal_hourly and (not self.resource_calendar_id or self.resource_calendar_id == cal_monthly):
                self.resource_calendar_id = cal_hourly
            if hasattr(self, "ruleset_id") and not self.ruleset_id:
                arg_ruleset = self.env.ref("payroll_arg_attendance.ruleset_jornales_arg_lct", raise_if_not_found=False)
                if not arg_ruleset:
                    arg_ruleset = self.env.ref("hr_attendance.hr_attendance_default_ruleset", raise_if_not_found=False)
                if arg_ruleset:
                    self.ruleset_id = arg_ruleset
            if self.labor_category_id and self.labor_category_id.category_type != "hourly":
                self.labor_category_id = False
        else:
            self.schedule_pay = "monthly"
            struct = self._get_default_struct("monthly")
            if struct:
                self.struct_id = struct
            cal_hourly = self._get_default_calendar("hourly")
            cal_monthly = self._get_default_calendar("monthly")
            if cal_monthly and (not self.resource_calendar_id or self.resource_calendar_id == cal_hourly):
                self.resource_calendar_id = cal_monthly
            if self.labor_category_id and self.labor_category_id.category_type != "monthly":
                self.labor_category_id = False

    @api.onchange("struct_id")
    def _onchange_struct_id(self):
        if self.struct_id:
            if self.struct_id.code in HOURLY_STRUCT_CODES:
                self.wage_type = "hourly"
                self.schedule_pay = "bi-weekly"
                cal_hourly = self._get_default_calendar("hourly")
                cal_monthly = self._get_default_calendar("monthly")
                if cal_hourly and (not self.resource_calendar_id or self.resource_calendar_id == cal_monthly):
                    self.resource_calendar_id = cal_hourly
            elif self.struct_id.code in MONTHLY_STRUCT_CODES:
                self.wage_type = "monthly"
                self.schedule_pay = "monthly"
                cal_hourly = self._get_default_calendar("hourly")
                cal_monthly = self._get_default_calendar("monthly")
                if cal_monthly and (not self.resource_calendar_id or self.resource_calendar_id == cal_hourly):
                    self.resource_calendar_id = cal_monthly

    @api.onchange("labor_category_id", "wage_type")
    def _onchange_labor_category(self):
        if self.labor_category_id:
            if not self.cct_id and self.labor_category_id.cct_id:
                self.cct_id = self.labor_category_id.cct_id
            if self.wage_type == "hourly" and self.labor_category_id.hourly_wage:
                self.wage = self.labor_category_id.hourly_wage
            elif self.wage_type == "monthly" and self.labor_category_id.monthly_wage:
                self.wage = self.labor_category_id.monthly_wage

    # ──────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            cat_id = vals.get("labor_category_id")
            if cat_id:
                cat = self.env["afip.labor.category"].browse(cat_id)
                if cat.category_type and "wage_type" not in vals:
                    vals["wage_type"] = cat.category_type
                w_type = vals.get("wage_type", "monthly")
                if not vals.get("wage"):
                    vals["wage"] = cat.hourly_wage if w_type == "hourly" else cat.monthly_wage
                if w_type == "hourly":
                    if "schedule_pay" not in vals:
                        vals["schedule_pay"] = "bi-weekly"
                    if "struct_id" not in vals:
                        struct = self._get_default_struct("hourly")
                        if struct:
                            vals["struct_id"] = struct.id
                    if "resource_calendar_id" not in vals:
                        cal = self._get_default_calendar("hourly")
                        if cal:
                            vals["resource_calendar_id"] = cal.id
                elif w_type == "monthly":
                    if "schedule_pay" not in vals:
                        vals["schedule_pay"] = "monthly"
                    if "struct_id" not in vals:
                        struct = self._get_default_struct("monthly")
                        if struct:
                            vals["struct_id"] = struct.id
                    if "resource_calendar_id" not in vals:
                        cal = self._get_default_calendar("monthly")
                        if cal:
                            vals["resource_calendar_id"] = cal.id

        try:
            return super().create(vals_list)
        except ValidationError as e:
            if e.__context__ and isinstance(e.__context__, ValidationError):
                raise e.__context__ from None
            raise

    def write(self, vals):
        cat_id = vals.get("labor_category_id")
        if not cat_id:
            return self._write_unwrapping_errors(vals)
        cat = self.env["afip.labor.category"].browse(cat_id)
        for rec in self:
            rec_vals = dict(vals)
            if cat.category_type and "wage_type" not in vals and rec.wage_type != cat.category_type:
                rec_vals["wage_type"] = cat.category_type
            # El sueldo sólo sigue a la categoría si no fue pactado distinto al de la categoría anterior
            old_cat = rec.labor_category_id
            wage_is_default = not rec.wage or rec.wage in (old_cat.hourly_wage, old_cat.monthly_wage)
            if "wage" not in vals and wage_is_default:
                target_type = rec_vals.get("wage_type") or rec.wage_type or "monthly"
                rec_vals["wage"] = cat.hourly_wage if target_type == "hourly" else cat.monthly_wage
            rec._write_unwrapping_errors(rec_vals)
        return True

    def _write_unwrapping_errors(self, vals):
        try:
            return super().write(vals)
        except ValidationError as e:
            if e.__context__ and isinstance(e.__context__, ValidationError):
                raise e.__context__ from None
            raise
