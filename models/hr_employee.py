# -*- coding: utf-8 -*-
"""@file
Ficha del empleado para la nómina argentina: CUIL, legajo, forma de pago y CBU, obra social, aporte
adicional de Seguridad Social y deducciones de Ganancias (cargas de familia y F.572 SIRADIG).

En Odoo 19 los datos del contrato (tipo de salario, estructura, convenio) se editan también desde el
empleado (versión actual); por eso las restricciones y onchanges del contrato tienen su espejo acá.
"""
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def validate_cuit_cuil(cuit_str):
    """Valida el dígito verificador de un CUIT / CUIL (módulo 11, pesos 5-4-3-2-7-6-5-4-3-2).

    @param cuit_str CUIT o CUIL, con o sin guiones. Vacío se considera válido (campo opcional).
    @return True si es válido.
    """
    if not cuit_str:
        return True
    cuit = cuit_str.replace("-", "").strip()
    if len(cuit) != 11 or not cuit.isdigit():
        return False
    multipliers = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(cuit[i]) * multipliers[i] for i in range(10))
    mod = total % 11
    verif = 11 - mod
    if verif == 11:
        verif = 0
    elif verif == 10:
        verif = 9
    return int(cuit[10]) == verif


class HrEmployee(models.Model):
    """Empleado con los datos personales, bancarios y fiscales que pide la liquidación argentina."""

    _inherit = "hr.employee"

    cuil = fields.Char(string="CUIL", size=11, index=True, help="11 dígitos numéricos sin guiones")
    legajo = fields.Integer(string="N° de Legajo", index=True, help="Número de legajo del trabajador")
    cbu = fields.Char(string="CBU Bancario", size=22, help="Clave Bancaria Uniforme (22 dígitos)")
    payment_type = fields.Selection(
        [
            ("1", "Efectivo"),
            ("2", "Cheque"),
            ("3", "Acreditación en Cuenta (CBU)"),
        ],
        string="Forma de Pago",
        default="3",
        help="Código de forma de pago ante AFIP",
    )

    health_insurance_id = fields.Many2one("afip.health.insurance", string="Obra Social (RNOS)")
    health_insurance_adherents = fields.Integer(string="Adherentes Obra Social", default=0)
    workplace_location = fields.Char(string="Lugar de Trabajo", default="Córdoba")
    aporte_adicional_ss_monto = fields.Float(
        string="Aporte Adicional Seg. Social ($)",
        default=0.0,
        help="Monto fijo en pesos a descontar de la liquidación en la 2da quincena como Aporte Adicional de Seguridad Social.",
    )

    # Deducciones Personales de Ganancias 4ta Categoría (SIRADIG F.572)
    ganancias_conyuge = fields.Boolean(string="Declara Cónyuge a Cargo", default=False)
    ganancias_hijos = fields.Integer(string="Hijos a Cargo", default=0)
    ganancias_hijos_incapacitados = fields.Integer(string="Hijos Incapacitados a Cargo", default=0)
    ganancias_otras_deducciones_mensual = fields.Float(
        string="Otras Deducciones Mensuales SIRADIG ($)",
        default=0.0,
        help="Prepagas, alquileres, intereses hipotecarios, etc. declarados mensualmente en F.572 Web.",
    )
    siradig_f572_ids = fields.One2many(
        "hr.siradig.f572",
        "employee_id",
        string="Declaraciones SIRADIG F.572",
        help="Historial de formularios F.572 Web presentados por el empleado en AFIP.",
    )
    siradig_count = fields.Integer(
        string="Cantidad F.572",
        compute="_compute_siradig_count",
    )
    siradig_latest_id = fields.Many2one(
        "hr.siradig.f572",
        string="Último F.572 Registrado",
        compute="_compute_siradig_latest_id",
        store=True,
    )

    @api.depends("siradig_f572_ids")
    def _compute_siradig_count(self):
        """Cantidad de F.572 importados (botón inteligente)."""
        for emp in self:
            emp.siradig_count = len(emp.siradig_f572_ids)

    @api.depends("siradig_f572_ids")
    def _compute_siradig_latest_id(self):
        """Último F.572 según el orden del modelo (período fiscal, fecha y número de presentación)."""
        for emp in self:
            emp.siradig_latest_id = emp.siradig_f572_ids[:1] if emp.siradig_f572_ids else False

    def action_view_siradig_f572(self):
        """Lista de los F.572 del empleado (botón inteligente).

        @return Acción de ventana.
        """
        self.ensure_one()
        return {
            "name": f"Declaraciones SIRADIG F.572 - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "hr.siradig.f572",
            "view_mode": "list,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id, "default_cuit_empleado": self.cuil or self.identification_id},
        }

    def action_reapply_latest_siradig(self):
        """Vuelve a aplicar a la ficha el último F.572 importado (cargas de familia y deducción mensual).

        @return Notificación de `hr.siradig.f572.action_apply_to_employee()`.
        @throws UserError Si el empleado no tiene ningún F.572.

        @bug T1 (docs/revision.md): `UserError` no está importado en este archivo; sin F.572 el botón
             termina en NameError en lugar del mensaje.
        """
        self.ensure_one()
        latest = self.siradig_latest_id or (self.siradig_f572_ids and self.siradig_f572_ids[0])
        if not latest:
            raise UserError(f"El empleado '{self.name}' no tiene ninguna declaración F.572 importada.")
        return latest.action_apply_to_employee()

    # ──────────────────────────────────────────────
    # CONSTRAINS — Espejo de las del contrato, para proteger el empleado
    # ──────────────────────────────────────────────

    @api.constrains("wage_type", "struct_id")
    def _check_wage_type_vs_struct(self):
        """Impide estados incoherentes wage_type ↔ struct_id a nivel empleado.

        @throws ValidationError Si el tipo de salario no coincide con la estructura.
        """
        from .hr_contract import HOURLY_STRUCT_CODES, MONTHLY_STRUCT_CODES
        for emp in self:
            if not emp.struct_id:
                continue
            code = emp.struct_id.code
            if emp.wage_type == "hourly" and code in MONTHLY_STRUCT_CODES:
                raise ValidationError(
                    f"El empleado '{emp.name}' es Jornalizado pero tiene "
                    f"asignada la estructura mensual '{emp.struct_id.name}'."
                )
            if emp.wage_type == "monthly" and code in HOURLY_STRUCT_CODES:
                raise ValidationError(
                    f"El empleado '{emp.name}' es Mensualizado pero tiene "
                    f"asignada la estructura de jornales '{emp.struct_id.name}'."
                )

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    @api.model
    def _get_default_calendar(self, wage_type):
        """Delega al helper centralizado del contrato.

        @param wage_type 'hourly' o 'monthly'.
        @return resource.calendar o False.
        """
        return self.env["hr.version"]._get_default_calendar(wage_type)

    @api.model
    def _get_default_struct(self, wage_type, tipo_liquidacion=None):
        """Delega al helper centralizado del contrato.

        @param wage_type 'hourly' o 'monthly'.
        @param tipo_liquidacion Tipo de lote (opcional).
        @return hr.payroll.structure o False.
        """
        return self.env["hr.version"]._get_default_struct(wage_type, tipo_liquidacion=tipo_liquidacion)

    # ──────────────────────────────────────────────
    # ONCHANGES
    # ──────────────────────────────────────────────

    @api.onchange("wage_type")
    def _onchange_wage_type(self):
        """Sincroniza periodicidad, estructura y calendario con el tipo de salario; si la categoría es
        del otro tipo la limpia junto con el básico."""
        cal_jornal = self._get_default_calendar("hourly")
        cal_mensual = self._get_default_calendar("monthly")
        if self.wage_type == "hourly":
            self.schedule_pay = "bi-weekly"
            struct = self._get_default_struct("hourly")
            if struct:
                self.struct_id = struct
            if cal_jornal:
                self.resource_calendar_id = cal_jornal
            if self.labor_category_id and self.labor_category_id.category_type != "hourly":
                self.labor_category_id = False
                self.wage = 0.0
        else:
            self.schedule_pay = "monthly"
            struct = self._get_default_struct("monthly")
            if struct:
                self.struct_id = struct
            if cal_mensual:
                self.resource_calendar_id = cal_mensual
            if self.labor_category_id and self.labor_category_id.category_type != "monthly":
                self.labor_category_id = False
                self.wage = 0.0

    @api.onchange("labor_category_id")
    def _onchange_labor_category(self):
        """La categoría manda: CCT, tipo de salario y básico salen de ella."""
        if self.labor_category_id:
            if self.labor_category_id.cct_id:
                self.cct_id = self.labor_category_id.cct_id
            if self.labor_category_id.category_type:
                self.wage_type = self.labor_category_id.category_type
                if self.wage_type == "hourly":
                    self.wage = self.labor_category_id.hourly_wage
                else:
                    self.wage = self.labor_category_id.monthly_wage
                self._onchange_wage_type()

    @api.onchange("struct_id")
    def _onchange_struct_id(self):
        """Al elegir una estructura argentina, ajusta tipo de salario, periodicidad y calendario."""
        from .hr_contract import HOURLY_STRUCT_CODES, MONTHLY_STRUCT_CODES
        if self.struct_id:
            cal_jornal = self._get_default_calendar("hourly")
            cal_mensual = self._get_default_calendar("monthly")
            if self.struct_id.code in HOURLY_STRUCT_CODES:
                self.wage_type = "hourly"
                self.schedule_pay = "bi-weekly"
                if cal_jornal:
                    self.resource_calendar_id = cal_jornal
            elif self.struct_id.code in MONTHLY_STRUCT_CODES:
                self.wage_type = "monthly"
                self.schedule_pay = "monthly"
                if cal_mensual:
                    self.resource_calendar_id = cal_mensual

    @api.onchange("resource_calendar_id")
    def _onchange_resource_calendar(self):
        """Deduce tipo de salario y estructura del calendario elegido (ver el mismo método en
        `hr.version`, incluida su advertencia U2)."""
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

    # ──────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────

    def write(self, vals):
        """Evita crear una versión de contrato duplicada: si ya existe otra versión con esa fecha, no
        cambia la fecha de la versión actual.

        @param vals Valores a escribir.
        @return True.
        """
        if "date_version" in vals:
            target_date = fields.Date.to_date(vals["date_version"])
            for emp in self:
                existing = emp.version_ids.filtered(lambda v: v.date_version == target_date)
                if existing and emp.version_id not in existing:
                    vals = dict(vals)
                    vals.pop("date_version", None)
                    break
        return super().write(vals)

    # ──────────────────────────────────────────────
    # VALIDACIONES DE DATOS
    # ──────────────────────────────────────────────

    @api.constrains("cuil")
    def _check_cuil(self):
        """El CUIL debe tener dígito verificador válido (lo exigen el F.931 y el LSD).

        @throws ValidationError CUIL inválido.
        """
        for employee in self:
            if employee.cuil and not validate_cuit_cuil(employee.cuil):
                raise ValidationError(f"El CUIL '{employee.cuil}' del empleado '{employee.name}' no es válido.")

    @api.constrains("cbu")
    def _check_cbu(self):
        """El CBU debe tener 22 dígitos (archivos de acreditación bancaria). No valida los dígitos
        verificadores de la CBU.

        @throws ValidationError CBU con otro largo o con letras.
        """
        for employee in self:
            if employee.cbu:
                cbu_clean = employee.cbu.strip()
                if len(cbu_clean) != 22 or not cbu_clean.isdigit():
                    raise ValidationError(f"El CBU '{employee.cbu}' del empleado '{employee.name}' debe tener 22 dígitos numéricos.")
