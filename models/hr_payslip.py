import base64
import logging
import os
import tempfile
from datetime import datetime, time
import pytz

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from py_arg_reports.reporters.recibo_sueldo.base import ReciboDownloader
from .hr_contract import DIAS_BASE_MENSUAL_LCT, HOURLY_STRUCT_CODES, MONTHLY_STRUCT_CODES

_logger = logging.getLogger(__name__)

# Plus vacacional Art. 155 LCT — 20% sobre salario habitual
PLUS_VACACIONAL_ART_155 = 1.20


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    total_remunerativo = fields.Float(
        string="Total Remunerativo", compute="_compute_totals_arg", store=True
    )
    total_no_remunerativo = fields.Float(
        string="Total No Remunerativo", compute="_compute_totals_arg", store=True
    )
    total_retenciones = fields.Float(
        string="Total Retenciones", compute="_compute_totals_arg", store=True
    )
    neto_liquidacion = fields.Float(
        string="Neto a Cobrar", compute="_compute_totals_arg", store=True
    )
    total_contribuciones = fields.Float(
        string="Total Contribuciones Patronales", compute="_compute_totals_arg", store=True
    )
    costo_total_empleador = fields.Float(
        string="Costo Total Empleador", compute="_compute_totals_arg", store=True
    )
    contribucion_line_ids = fields.One2many(
        "hr.payslip.line",
        compute="_compute_contribucion_lines",
        string="Líneas de Contribuciones Patronales",
    )
    struct_id = fields.Many2one(
        "hr.payroll.structure",
        string="Estructura Salarial",
        readonly=False,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        required=True,
        readonly=False,
    )
    date_from = fields.Date(
        string="Desde",
        required=True,
        readonly=False,
    )
    date_to = fields.Date(
        string="Hasta",
        required=True,
        readonly=False,
    )

    # ──────────────────────────────────────────────
    # Campos de Liquidación: Horas (Jornal)
    # ──────────────────────────────────────────────
    hours_theoretical = fields.Float(
        string="Horas del Período",
        digits=(16, 2),
        readonly=True,
        default=0.0,
        help="Horas teóricas del período según el calendario de trabajo.",
    )
    hours_leaves = fields.Float(
        string="(-) Horas Ausencias / Vacaciones",
        digits=(16, 2),
        readonly=True,
        default=0.0,
        help="Horas correspondientes a licencias por vacaciones o ausencias a descontar.",
    )
    hours_normal = fields.Float(
        string="(=) Horas Netas a Liquidar",
        digits=(16, 2),
        default=0.0,
        help="Horas netas ordinarias efectivamente liquidadas (Horas Período - Horas Ausencias).",
    )
    hours_ext50 = fields.Float(
        string="(+) Horas Extras 50%",
        digits=(16, 2),
        readonly=True,
        default=0.0,
        help="Horas extras liquidadas al 50%.",
    )
    hours_ext100 = fields.Float(
        string="(+) Horas Extras 100%",
        digits=(16, 2),
        readonly=True,
        default=0.0,
        help="Horas extras liquidadas al 100%.",
    )
    total_hours_worked = fields.Float(
        string="Total Horas a Cobrar",
        digits=(16, 2),
        readonly=True,
        default=0.0,
        help="Total de horas a cobrar en la quincena (Horas Netas + Extras).",
    )

    # ──────────────────────────────────────────────
    # Campos de Liquidación: Días (Mensual)
    # ──────────────────────────────────────────────
    days_theoretical = fields.Float(
        string="Días Base Período (30)",
        digits=(16, 2),
        readonly=True,
        default=30.0,
        help="Base legal estándar de días mensuales (30 días — Art. 155 LCT).",
    )
    total_days_vacation = fields.Float(
        string="(-) Días Vacaciones / Ausencias",
        digits=(16, 2),
        readonly=True,
        default=0.0,
        help="Días gozados de vacaciones u otras licencias en el mes.",
    )
    total_days_worked = fields.Float(
        string="(=) Días Netos Trabajados a Liquidar",
        digits=(16, 2),
        readonly=True,
        default=30.0,
        help="Días ordinarios de sueldo básico a liquidar (30 - Días Vacaciones).",
    )

    # ──────────────────────────────────────────────
    # Campos de Trazabilidad (F6)
    # ──────────────────────────────────────────────
    hours_source = fields.Char(
        string="Origen de Horas",
        readonly=True,
        help="Documenta de dónde se obtuvieron las horas liquidadas.",
    )
    days_source = fields.Char(
        string="Origen de Días",
        readonly=True,
        help="Documenta de dónde se obtuvieron los días liquidados.",
    )
    vacation_source = fields.Char(
        string="Origen Vacaciones",
        readonly=True,
        help="Documenta de dónde se obtuvieron los días de vacaciones.",
    )

    # ──────────────────────────────────────────────
    # Campos related del contrato
    # ──────────────────────────────────────────────
    cct_id = fields.Many2one(related="contract_id.cct_id", readonly=True, string="Convenio (CCT)")
    labor_category_id = fields.Many2one(
        related="contract_id.labor_category_id", readonly=True, string="Categoría Laboral"
    )
    wage_type = fields.Selection(related="contract_id.wage_type", readonly=True, string="Tipo de Salario")
    contract_wage = fields.Float(
        string="Básico / Valor Hora", compute="_compute_contract_wage", digits=(16, 2)
    )

    @api.depends("contract_id", "contract_id.wage")
    def _compute_contract_wage(self):
        for slip in self:
            slip.contract_wage = float(slip.contract_id.wage) if (slip.contract_id and slip.contract_id.wage) else 0.0

    # ──────────────────────────────────────────────
    # Tope Imponible de Retenciones (Art. 9 Ley 24.241)
    # ──────────────────────────────────────────────
    tope_imponible_retenciones = fields.Float(
        string="Tope Imponible Retenciones ($)",
        help="Base imponible máxima aplicable a retenciones de Seguridad Social para esta liquidación. Congelado al calcular.",
    )
    base_imponible_seg_social = fields.Float(
        string="Base Imponible Seg. Social ($)",
        compute="_compute_base_imponible_seg_social",
        store=True,
        help="Base imponible efectiva sujeta a retenciones de Seguridad Social (min(Remunerativo, Tope)).",
    )
    is_tope_applied = fields.Boolean(
        string="Tope Aplicado",
        compute="_compute_base_imponible_seg_social",
        store=True,
    )

    # ──────────────────────────────────────────────
    # Parámetros Históricos (Snapshots no inferibles de la tabla de líneas)
    # ──────────────────────────────────────────────
    snapshot_tope_imponible = fields.Float(string="Snapshot Tope Imponible ($)", store=True)
    snapshot_detraccion_sipa = fields.Float(string="Snapshot Detracción SIPA ($)", store=True)
    snapshot_art_fixed_fee = fields.Float(string="Snapshot Cuota Fija ART ($)", store=True)

    # ──────────────────────────────────────────────
    # Novedades Variables de la Quincena
    # ──────────────────────────────────────────────
    premio_prod_ok = fields.Boolean(
        string="Premio Prod.",
        default=False,
        help="Marcar si el empleado cobra Premio Producción esta quincena. "
             "El monto se toma del campo 'Monto Premio Producción' del lote.",
    )
    presentismo_ok = fields.Boolean(
        string="Presentismo",
        default=False,
        help="Marcar si el empleado cobra Presentismo esta quincena. "
             "El monto se toma del campo 'Monto Presentismo' del lote.",
    )
    portitulo_ok = fields.Boolean(
        string="Portítulo",
        default=False,
        help="Marcar si el empleado cobra Portítulo esta quincena. "
             "El monto se toma del campo 'Monto Portítulo' del lote.",
    )
    monto_objetivos = fields.Float(
        string="Objetivos ($)",
        default=0.0,
        help="Monto individual de Objetivos para este empleado en esta quincena. "
             "Se carga directamente porque varía por empleado.",
    )
    cant_feriados = fields.Float(
        string="Feriados (Hs)",
        compute="_compute_cant_feriados",
        store=True,
        readonly=False,
        help="Cantidad de horas de feriado a liquidar en esta quincena.",
    )
    feriados_manual = fields.Boolean(
        string="Feriados Manual",
        default=False,
    )
    gratif_no_rem_ok = fields.Boolean(
        string="Gratif. NR",
        default=True,
        help="Aplica Gratificación Extraordinaria No Remunerativa en este recibo.",
    )
    monto_gratif_no_rem = fields.Float(
        string="Monto Gratif. NR ($)",
        compute="_compute_monto_gratif_no_rem",
        store=True,
        readonly=False,
        help="Monto de la Gratificación No Remunerativa. Se toma del lote o puede modificarse individualmente.",
    )
    gratif_no_rem_manual = fields.Boolean(
        string="Gratificación Manual",
        default=False,
    )
    compens_no_rem_ok = fields.Boolean(
        string="Compens. NR",
        default=True,
        help="Aplica Compensación Extraordinaria No Remunerativa en este recibo.",
    )
    monto_compens_no_rem = fields.Float(
        string="Monto Compens. NR ($)",
        compute="_compute_monto_compens_no_rem",
        store=True,
        readonly=False,
        help="Monto de la Compensación No Remunerativa. Se toma del lote o puede modificarse individualmente.",
    )
    compens_no_rem_manual = fields.Boolean(
        string="Compensación Manual",
        default=False,
    )
    cant_viandas = fields.Float(
        string="Cant. Viandas",
        default=0.0,
        digits=(16, 2),
        help="Cantidad de viandas a descontar en la quincena.",
    )
    precio_vianda = fields.Float(
        string="Precio Vianda ($)",
        compute="_compute_precio_vianda",
        store=True,
        readonly=False,
        digits=(16, 2),
        help="Precio unitario de la vianda a descontar. Se toma del lote o puede modificarse individualmente.",
    )
    precio_vianda_manual = fields.Boolean(
        string="Precio Vianda Manual",
        default=False,
    )
    antiguedad_override = fields.Boolean(
        string="Override Antigüedad",
        default=False,
        help="Si se activa, el Adicional Antigüedad usa los años cargados a mano en vez de los "
             "calculados desde la fecha de ingreso.",
    )
    antiguedad_anios_manual = fields.Integer(
        string="Antigüedad Manual (Años)",
        default=0,
    )
    antiguedad_anios = fields.Integer(
        string="Antigüedad (Años)",
        compute="_compute_antiguedad_anios",
        store=True,
        help="Años de antigüedad efectivos usados por el Adicional Antigüedad "
             "(override manual o calculado desde la fecha de ingreso).",
    )
    coef_contrib_ss = fields.Float(
        string="Coef. Contrib. Seg. Social",
        compute="_compute_coef_contrib",
        store=True,
        readonly=False,
        digits=(16, 4),
        help="Coeficiente aplicado sobre Jubilación, Ley 19.032, AAFF y FNE patronales "
             "(cantidad de la línea). Se toma del lote o puede modificarse individualmente.",
    )
    coef_contrib_os = fields.Float(
        string="Coef. Contrib. Obra Social",
        compute="_compute_coef_contrib",
        store=True,
        readonly=False,
        digits=(16, 4),
        help="Coeficiente aplicado sobre la contribución patronal de Obra Social "
             "(cantidad de la línea). Se toma del lote o puede modificarse individualmente.",
    )
    tipo_liquidacion = fields.Selection(
        related="payslip_run_id.tipo_liquidacion",
        string="Tipo de Liquidación",
        readonly=True,
        store=True,
    )
    is_quincenal = fields.Boolean(
        string="Es Liquidación Quincenal",
        compute="_compute_is_quincenal",
        store=True,
        help="Indica si el recibo corresponde a una liquidación quincenal.",
    )
    payment_date = fields.Date(
        string="Fecha de Pago",
        compute="_compute_payment_date",
        store=True,
        readonly=False,
        help="Fecha efectiva de pago de los haberes. Por defecto toma la última fecha del período o la del lote de liquidación.",
    )

    @api.depends("payslip_run_id.payment_date", "date_to")
    def _compute_payment_date(self):
        for slip in self:
            if slip.payslip_run_id and slip.payslip_run_id.payment_date:
                slip.payment_date = slip.payslip_run_id.payment_date
            elif slip.date_to:
                slip.payment_date = slip.date_to
            elif not slip.payment_date:
                slip.payment_date = fields.Date.today()

    # ──────────────────────────────────────────────
    # Impuesto a las Ganancias 4ta Categoría
    # ──────────────────────────────────────────────
    ganancias_override = fields.Float(
        string="Override Retención Ganancias ($)",
        default=0.0,
        help="Si se especifica un importe > 0, se aplica directamente como retención de Ganancias sin usar el cálculo automático.",
    )
    ganancias_amount = fields.Float(
        string="Retención Ganancias del Mes ($)",
        compute="_compute_ganancias_fields",
        store=True,
    )
    has_ganancias_retention = fields.Boolean(
        string="Retiene Ganancias",
        compute="_compute_ganancias_fields",
        store=True,
    )
    ganancias_status = fields.Char(
        string="Estado Ganancias",
        compute="_compute_ganancias_fields",
        store=True,
    )

    # ──────────────────────────────────────────────
    # Base Patronal Jornales (Mes Anterior)
    # ──────────────────────────────────────────────
    prev_month_gross_arca = fields.Float(
        string="Bruto Mes Anterior (Jornales)",
        compute="_compute_prev_month_gross",
        store=True,
        readonly=False,
        help="Base imponible del mes anterior tomada de liquidaciones en el sistema para contribuciones patronales de operarios jornalizados.",
    )
    prev_month_gross_manual = fields.Float(
        string="Bruto Mes Anterior Manual ($)",
        default=0.0,
        help="Permite ingresar manualmente el bruto del mes anterior si el empleado es nuevo o no tiene recibos previos cargados en Odoo.",
    )

    @api.depends("total_remunerativo", "tope_imponible_retenciones")
    def _compute_base_imponible_seg_social(self):
        for slip in self:
            tope = slip.tope_imponible_retenciones
            rem = slip.total_remunerativo
            if tope and tope > 0:
                slip.base_imponible_seg_social = round(min(rem, tope), 2)
                slip.is_tope_applied = rem > tope
            else:
                slip.base_imponible_seg_social = round(rem, 2)
                slip.is_tope_applied = False

    @api.depends("employee_id", "date_from", "prev_month_gross_manual")
    def _compute_prev_month_gross(self):
        from dateutil.relativedelta import relativedelta
        import calendar
        for slip in self:
            if slip.prev_month_gross_manual > 0:
                slip.prev_month_gross_arca = round(slip.prev_month_gross_manual, 2)
                continue

            if not slip.employee_id or not slip.date_from:
                slip.prev_month_gross_arca = 0.0
                continue

            prev_date = slip.date_from - relativedelta(months=1)
            first_day_prev = prev_date.replace(day=1)
            last_day_num = calendar.monthrange(prev_date.year, prev_date.month)[1]
            last_day_prev = prev_date.replace(day=last_day_num)

            past_slips = self.search([
                ("employee_id", "=", slip.employee_id.id),
                ("id", "!=", slip.id if slip.id else 0),
                ("date_from", ">=", first_day_prev),
                ("date_to", "<=", last_day_prev),
                ("state", "in", ("done", "verify")),
            ])
            gross = sum(s.total_remunerativo for s in past_slips)
            slip.prev_month_gross_arca = round(gross, 2)

    @api.depends("line_ids", "line_ids.total", "ganancias_override")
    def _compute_ganancias_fields(self):
        for slip in self:
            line = slip.line_ids.filtered(lambda l: l.code == "RET_GANANCIAS")
            amt = abs(line[0].total) if line else 0.0
            if slip.ganancias_override > 0:
                amt = slip.ganancias_override
            slip.ganancias_amount = round(amt, 2)
            slip.has_ganancias_retention = amt > 0
            if slip.ganancias_override > 0:
                slip.ganancias_status = f"Override Manual ($ {amt:,.2f})"
            elif amt > 0:
                slip.ganancias_status = f"⚠️ Retiene Ganancias ($ {amt:,.2f})"
            else:
                slip.ganancias_status = "Exento / No Alcanzado"

    def _capture_historical_snapshots(self):
        """Captura y congela en el recibo todas las variables globales y topes vigentes."""
        for slip in self:
            company = slip.company_id or self.env.company
            contract = slip.contract_id

            # Si no tiene tope asignado en borrador, sugerir el estándar
            if not slip.tope_imponible_retenciones and slip.state == "draft":
                base_tope = company.tope_imponible_max_retencion or 4250000.0
                slip.tope_imponible_retenciones = round(base_tope / 2.0 if slip.is_quincenal else base_tope, 2)

            slip.snapshot_tope_imponible = slip.tope_imponible_retenciones
            slip.snapshot_detraccion_sipa = company.detraccion_sipa or 7003.68
            slip.snapshot_art_fixed_fee = company.art_fixed_fee or 1300.0

    def _calculate_ganancias_from_rules(self, cur_gross, cur_mandatory_ret):
        """Calcula Ganancias acumulativo desde la regla salarial RET_GANANCIAS."""
        self.ensure_one()
        if self.ganancias_override > 0:
            return round(self.ganancias_override, 2)

        target_date = self.date_to or fields.Date.today()
        year = target_date.year
        month = target_date.month

        scale = self.env["hr.ganancias.scale"].get_scale_for_date(target_date)
        if not scale:
            return 0.0

        acc_model = self.env["hr.ganancias.accumulator"]
        past_accumulators = acc_model.search([
            ("employee_id", "=", self.employee_id.id),
            ("year", "=", year),
            ("month", "<", month),
        ], order="month asc")

        prior_gross = sum(a.gross_rem for a in past_accumulators)
        prior_ded = sum(a.deductions_employee + a.other_deductions for a in past_accumulators)
        prior_retained = sum(a.retention_applied for a in past_accumulators)

        cur_ded = abs(cur_mandatory_ret)
        # Deducciones SIRADIG del mes:
        # Prioridad 1: Entrada manual en "Otras Entradas" (DED_SIRADIG) del recibo
        # Prioridad 2: Deducción mensual registrada en la ficha del empleado / último F.572
        siradig_input = self.input_line_ids.filtered(lambda i: i.code == "DED_SIRADIG")
        if siradig_input and siradig_input[0].amount > 0:
            cur_other_ded = siradig_input[0].amount
        else:
            cur_other_ded = self.employee_id.ganancias_otras_deducciones_mensual or 0.0

        tot_gross = prior_gross + cur_gross
        tot_mandatory_ded = prior_ded + cur_ded + cur_other_ded

        factor_mes = min(max(month, 1), 12) / 12.0
        emp = self.employee_id
        personal_ded = (
            (scale.deduccion_ganancia_no_imponible or 0.0) +
            (scale.deduccion_especial or 0.0) +
            ((scale.deduccion_conyuge or 0.0) if emp.ganancias_conyuge else 0.0) +
            ((scale.deduccion_hijo or 0.0) * (emp.ganancias_hijos or 0)) +
            ((scale.deduccion_hijo_incapacitado or 0.0) * (emp.ganancias_hijos_incapacitados or 0))
        ) * factor_mes

        net_taxable = max(0.0, tot_gross - tot_mandatory_ded - personal_ded)
        tax_accumulated = scale.calculate_annual_bracket(net_taxable, month)
        retention_this_month = max(0.0, round(tax_accumulated - prior_retained, 2))

        ret_applied = self.ganancias_override if self.ganancias_override > 0 else retention_this_month

        acc = acc_model.search([
            ("employee_id", "=", self.employee_id.id),
            ("year", "=", year),
            ("month", "=", month),
        ], limit=1)
        vals = {
            "employee_id": self.employee_id.id,
            "year": year,
            "month": month,
            "gross_rem": cur_gross,
            "deductions_employee": cur_ded,
            "other_deductions": cur_other_ded,
            "accumulated_gross": tot_gross,
            "accumulated_deductions": tot_mandatory_ded,
            "personal_deductions": personal_ded,
            "accumulated_net_taxable": net_taxable,
            "accumulated_tax": tax_accumulated,
            "accumulated_retained": prior_retained,
            "retention_calculated": retention_this_month,
            "retention_applied": ret_applied,
            "payslip_id": self.id,
        }
        if acc:
            acc.write(vals)
        else:
            acc_model.create(vals)

        return retention_this_month

    # ══════════════════════════════════════════════
    # MÉTODOS CENTRALIZADOS DE RESOLUCIÓN (F2)
    # ══════════════════════════════════════════════

    def _get_calendar_hours_for_period(self, calendar, date_from, date_to):
        """Calcula las horas teóricas del período desde el resource.calendar.

        FUENTE ÚNICA de horas teóricas — NO se hardcodean valores.

        Args:
            calendar: resource.calendar record
            date_from: date
            date_to: date

        Returns:
            float: horas teóricas del período
        """
        if not calendar or not date_from or not date_to:
            return 0.0

        total_days = (date_to - date_from).days + 1

        # Calcular horas semanales agrupando por (día, turno) para inmunizar contra registros duplicados
        daily_hours = {}
        for s in calendar.attendance_ids.filtered(lambda a: a.day_period != "lunch"):
            key = (s.dayofweek, s.day_period)
            dur = s.hour_to - s.hour_from
            if key not in daily_hours or dur > daily_hours[key]:
                daily_hours[key] = dur

        if daily_hours:
            weekly_hours = round(sum(daily_hours.values()), 2)
        else:
            weekly_hours = calendar.full_time_required_hours or (calendar.hours_per_day * 5) or 44.0

        if weekly_hours <= 0:
            return 0.0

        # Para quincenas (≤16 días): esquema de dos semanas = horas semanales × 2
        # Ej: 44 hs/sem × 2 = 88.0 hs quincenales; 40 hs/sem × 2 = 80.0 hs quincenales
        if total_days <= 16:
            return round(weekly_hours * 2.0, 1)
        else:
            return round(weekly_hours * (total_days / 7.0), 1)

    @api.model
    def _compute_attendance_hours_breakdown(self, attendances, calendar=None, employee=None):
        """Desglosa las horas de asistencia en normales, extras 50% y extras 100%
        utilizando directamente el motor nativo de Horas Extras de Odoo 19 (hr.attendance.overtime.line).

        Reglas estándar:
        - Horas Extras 100%:
            * Líneas de horas extras con amount_rate >= 2.0
            * O reglas asociadas a días no laborables (timing_type == 'non_work_days')
            * O reglas con '100' en su nombre, 'non working', 'domingo' o 'feriado'.
        - Horas Extras 50%:
            * Líneas de horas extras con amount_rate == 1.5
            * O reglas con '50' en su nombre o exceso de jornada habitual (schedule/quantity).
        - Horas Normales:
            * Total horas trabajadas menos horas extras computadas.
        """
        if not attendances:
            return {"hours_normal": 0.0, "hours_ext50": 0.0, "hours_ext100": 0.0}

        emp = employee or attendances[0].employee_id
        company = emp.company_id if emp else self.env.company
        validation_mode = getattr(company, "attendance_overtime_validation", "no_validation")

        tot_worked = sum(att.worked_hours for att in attendances if att.worked_hours > 0)
        tot_ext50 = 0.0
        tot_ext100 = 0.0

        # 1. Obtener las líneas de horas extras nativas vinculadas a estas asistencias
        ot_lines = attendances.mapped("linked_overtime_ids")
        if not ot_lines and emp and "hr.attendance.overtime.line" in self.env:
            min_date = min(att.date for att in attendances if att.date)
            max_date = max(att.date for att in attendances if att.date)
            ot_lines = self.env["hr.attendance.overtime.line"].search([
                ("employee_id", "=", emp.id),
                ("date", ">=", min_date),
                ("date", "<=", max_date),
            ])

        if ot_lines:
            for line in ot_lines:
                # Validar aprobación si la empresa lo exige
                if validation_mode == "by_manager" and line.status != "approved":
                    continue
                elif line.status == "refused":
                    continue

                duration = line.duration or line.manual_duration or 0.0
                if duration <= 0:
                    continue

                rate = line.amount_rate or 1.0
                rule_names = " ".join((r.name or "") for r in line.rule_ids).lower()
                timing_types = [r.timing_type for r in line.rule_ids if r.timing_type]

                # Clasificación:
                is_100 = (
                    rate >= 2.0
                    or "100" in rule_names
                    or "non_work_days" in timing_types
                    or "non working" in rule_names
                    or "domingo" in rule_names
                    or "feriado" in rule_names
                )
                is_50 = (
                    rate == 1.5
                    or "50" in rule_names
                    or (not is_100 and ("schedule" in timing_types or "work_days" in timing_types or "employee schedule" in rule_names))
                )

                if is_100:
                    tot_ext100 += duration
                elif is_50:
                    tot_ext50 += duration
                else:
                    tot_ext50 += duration
        else:
            # Fallback en caso de asistencias sin líneas generadas en hr.attendance.overtime.line
            tz_name = (calendar.tz if calendar else False) or (emp.tz if emp else False) or "America/Argentina/Cordoba"
            tz = pytz.timezone(tz_name)
            for att in attendances:
                ot_h = (att.validated_overtime_hours if validation_mode == "by_manager" else att.overtime_hours) or 0.0
                if ot_h > 0:
                    local_in = pytz.utc.localize(att.check_in).astimezone(tz)
                    if local_in.weekday() in (5, 6):  # Sábado o Domingo
                        tot_ext100 += ot_h
                    else:
                        tot_ext50 += ot_h

        tot_ext = tot_ext50 + tot_ext100
        tot_norm = max(0.0, tot_worked - tot_ext)

        return {
            "hours_normal": round(tot_norm, 2),
            "hours_ext50": round(tot_ext50, 2),
            "hours_ext100": round(tot_ext100, 2),
        }

    def _resolve_vacation_days(self):
        """Resuelve los días de vacaciones con cascada documentada.

        CASCADA DE PRIORIDAD:
        1. Otras Entradas (input_line_ids.VAC_DIAS) — override manual del usuario
        2. hr_holidays — ausencias aprobadas tipo vacaciones en el período
        3. 0.0 — sin vacaciones

        Returns:
            tuple(float, str): (días_vacaciones, descripción_fuente)
        """
        self.ensure_one()

        # Prioridad 1: Entrada manual en "Otras Entradas"
        vac_input = self.input_line_ids.filtered(lambda i: i.code == "VAC_DIAS")
        if vac_input and vac_input[0].amount > 0:
            return vac_input[0].amount, "Entrada manual: VAC_DIAS"

        # Prioridad 2: hr_holidays (ausencias aprobadas)
        vac_days = self._get_vacation_days_from_leaves()
        if vac_days > 0:
            return vac_days, "hr_holidays: ausencias aprobadas en el período"

        return 0.0, "Sin vacaciones en el período"

    def _resolve_liquidation_hours(self, force_external=False):
        """Resuelve las horas a liquidar con cascada explícita y documentada.

        CASCADA DE PRIORIDAD (jornal):
        1. Otras Entradas (input_line_ids: HS_NORM, HS_EXT50, HS_EXT100) — si el usuario modificó manualmente
        2. Asistencias registradas (hr.attendance) — fichadas del reloj/fichero
        3. Resource Calendar (resource_calendar_id) — horas teóricas del calendario laboral
        4. Error / 0.0 — no se puede liquidar sin dato de origen
        """
        self.ensure_one()
        contract = self.contract_id
        cal = contract.resource_calendar_id if contract else False

        vac_days, vac_source = self._resolve_vacation_days()
        hours_per_day = cal.hours_per_day if cal and cal.hours_per_day else 8.0

        tipo_liq = self.payslip_run_id.tipo_liquidacion if self.payslip_run_id else None
        if tipo_liq == "Vacaciones":
            return {
                "hours_theoretical": 0.0,
                "hours_leaves": 0.0,
                "hours_normal": 0.0,
                "hours_ext50": 0.0,
                "hours_ext100": 0.0,
                "total_hours_worked": 0.0,
                "source": f"Lote Exclusivo Adelanto Vacaciones Jornal (Art. 155 LCT) — {vac_days} días",
                "vac_days": vac_days,
                "vac_source": vac_source,
            }
        elif tipo_liq == "SAC":
            return {
                "hours_theoretical": 0.0,
                "hours_leaves": 0.0,
                "hours_normal": 0.0,
                "hours_ext50": 0.0,
                "hours_ext100": 0.0,
                "total_hours_worked": 0.0,
                "source": "Lote Exclusivo SAC Jornal (Aguinaldo Semestral)",
                "vac_days": 0.0,
                "vac_source": "No aplica para SAC",
            }

        ext50_input = self.input_line_ids.filtered(lambda i: i.code == "HS_EXT50")
        ext100_input = self.input_line_ids.filtered(lambda i: i.code == "HS_EXT100")
        norm_input = self.input_line_ids.filtered(lambda i: i.code == "HS_NORM")

        hs_ext50_val = ext50_input[0].amount if ext50_input else 0.0
        hs_ext100_val = ext100_input[0].amount if ext100_input else 0.0

        # Prioridad 1: Otras Entradas (si no se fuerza sincronización externa y existen inputs)
        if not force_external and (norm_input or ext50_input or ext100_input):
            hs_norm = norm_input[0].amount if norm_input else 0.0
            cal_hours = self._get_calendar_hours_for_period(cal, self.date_from, self.date_to)
            hours_leaves = round(vac_days * hours_per_day, 2)
            source_parts = [f"{hs_norm} hs norm"]
            if hs_ext50_val > 0:
                source_parts.append(f"{hs_ext50_val} hs ext 50%")
            if hs_ext100_val > 0:
                source_parts.append(f"{hs_ext100_val} hs ext 100%")
            return {
                "hours_theoretical": cal_hours if cal_hours > 0 else hs_norm + hours_leaves,
                "hours_leaves": hours_leaves,
                "hours_normal": hs_norm,
                "hours_ext50": hs_ext50_val,
                "hours_ext100": hs_ext100_val,
                "total_hours_worked": round(hs_norm + hs_ext50_val + hs_ext100_val, 2),
                "source": "Otras Entradas: " + ", ".join(source_parts),
                "vac_days": vac_days,
                "vac_source": vac_source,
            }

        # Buscar asistencias si existen en la BD (fichero / reloj)
        att_breakdown = {"hours_normal": 0.0, "hours_ext50": 0.0, "hours_ext100": 0.0}
        if "hr.attendance" in self.env and self.employee_id and self.date_from and self.date_to:
            try:
                tz = pytz.timezone(cal.tz or self.employee_id.tz or "America/Argentina/Cordoba") if cal else pytz.utc
                tz_start = tz.localize(datetime.combine(self.date_from, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
                tz_end = tz.localize(datetime.combine(self.date_to, time.max)).astimezone(pytz.utc).replace(tzinfo=None)
                attendances = self.env["hr.attendance"].search([
                    ("employee_id", "=", self.employee_id.id),
                    ("check_in", ">=", tz_start),
                    ("check_in", "<=", tz_end),
                    ("check_out", "!=", False),
                ])
                if attendances:
                    att_breakdown = self._compute_attendance_hours_breakdown(attendances, calendar=cal, employee=self.employee_id)
            except Exception as e:
                _logger.warning("Error buscando asistencias para %s: %s", self.employee_id.name, e)

        # Prioridad 2: Asistencias registradas (hr.attendance)
        att_total = att_breakdown["hours_normal"] + att_breakdown["hours_ext50"] + att_breakdown["hours_ext100"]
        if att_total > 0.1:
            cal_hours = self._get_calendar_hours_for_period(cal, self.date_from, self.date_to)
            hours_leaves = round(vac_days * hours_per_day, 2)
            hs_norm = att_breakdown["hours_normal"]
            final_ext50 = att_breakdown["hours_ext50"]
            final_ext100 = att_breakdown["hours_ext100"]
            source_parts = [f"{hs_norm} hs norm"]
            if final_ext50 > 0:
                source_parts.append(f"{final_ext50} hs ext 50%")
            if final_ext100 > 0:
                source_parts.append(f"{final_ext100} hs ext 100%")
            return {
                "hours_theoretical": cal_hours if cal_hours > 0 else hs_norm,
                "hours_leaves": hours_leaves,
                "hours_normal": hs_norm,
                "hours_ext50": final_ext50,
                "hours_ext100": final_ext100,
                "total_hours_worked": round(hs_norm + final_ext50 + final_ext100, 2),
                "source": "Asistencias Reales: " + ", ".join(source_parts),
                "vac_days": vac_days,
                "vac_source": vac_source,
            }

        # Prioridad 3: Resource Calendar (fallback si no hay entradas ni asistencias)
        if cal:
            cal_hours = self._get_calendar_hours_for_period(cal, self.date_from, self.date_to)
            if cal_hours > 0:
                hours_leaves = round(vac_days * hours_per_day, 2)
                hs_norm = max(0.0, cal_hours - hours_leaves)
                source_txt = f"Calendario: {cal.name} ({cal.full_time_required_hours}h/sem)"
                return {
                    "hours_theoretical": cal_hours,
                    "hours_leaves": hours_leaves,
                    "hours_normal": hs_norm,
                    "hours_ext50": 0.0,
                    "hours_ext100": 0.0,
                    "total_hours_worked": hs_norm,
                    "source": source_txt,
                    "vac_days": vac_days,
                    "vac_source": vac_source,
                }

        # Sin dato de origen — retornar ceros con warning
        _logger.warning(
            "Payslip %s: no se pudo resolver horas — sin calendario ni entrada manual.",
            self.display_name,
        )
        return {
            "hours_theoretical": 0.0,
            "hours_leaves": 0.0,
            "hours_normal": 0.0,
            "hours_ext50": 0.0,
            "hours_ext100": 0.0,
            "total_hours_worked": 0.0,
            "source": "SIN DATOS — configure calendario o cargue HS_NORM en Otras Entradas",
            "vac_days": vac_days,
            "vac_source": vac_source,
        }

    def _resolve_liquidation_days(self):
        """Resuelve los días a liquidar para mensualizados.

        Base legal: 30 días (Art. 155 LCT) - días de vacaciones = días trabajados.

        Returns:
            dict con: days_theoretical, total_days_vacation, total_days_worked, source
        """
        self.ensure_one()
        vac_days, vac_source = self._resolve_vacation_days()
        tipo_liq = self.payslip_run_id.tipo_liquidacion if self.payslip_run_id else None

        if tipo_liq == "Vacaciones":
            days_worked = 0.0
            source = f"Lote Exclusivo Adelanto Vacaciones (Art. 155 LCT) — {vac_days} días"
        elif tipo_liq == "SAC":
            days_worked = 0.0
            vac_days = 0.0
            source = "Lote Exclusivo SAC (Aguinaldo Semestral)"
        else:
            days_worked = max(0.0, DIAS_BASE_MENSUAL_LCT - vac_days)
            source = f"Base legal {DIAS_BASE_MENSUAL_LCT} días (LCT Art. 155)"

        return {
            "days_theoretical": float(DIAS_BASE_MENSUAL_LCT) if tipo_liq not in ("Vacaciones", "SAC") else 0.0,
            "total_days_vacation": vac_days,
            "total_days_worked": days_worked,
            "source": source,
            "vac_source": vac_source,
        }

    # ══════════════════════════════════════════════
    # MÉTODO CENTRALIZADO DE SINCRONIZACIÓN (F4.1)
    # ══════════════════════════════════════════════

    def _sync_liquidation_summary(self, force_external=False):
        """Sincroniza el resumen de liquidación (horas o días) desde las fuentes resueltas.

        Este método es el ÚNICO punto donde se calculan y persisten los valores
        de horas/días del payslip. Se invoca desde:
        - onchange_employee (force_external=True)
        - onchange_struct_id (force_external=True)
        - _onchange_input_line_ids (force_external=False)
        - compute_sheet (force_external=False)
        """
        for slip in self:
            contract = slip.contract_id
            if not contract:
                continue

            is_hourly = contract.wage_type == "hourly"

            if is_hourly:
                data = slip._resolve_liquidation_hours(force_external=force_external)
                slip.hours_theoretical = data["hours_theoretical"]
                slip.hours_leaves = data["hours_leaves"]
                slip.hours_normal = data["hours_normal"]
                slip.hours_ext50 = data["hours_ext50"]
                slip.hours_ext100 = data["hours_ext100"]
                slip.total_hours_worked = data["total_hours_worked"]
                slip.hours_source = data["source"]

                slip.days_theoretical = 0.0
                slip.total_days_vacation = data["vac_days"]
                slip.total_days_worked = 0.0
                slip.days_source = ""
                slip.vacation_source = data["vac_source"]

                # Sincronizar input lines:
                # Asegurar que siempre existan las líneas de Horas Normales, Extras 50% y Extras 100% para que el usuario pueda cargarlas/modificarlas
                if force_external:
                    slip._sync_input_line("HS_NORM", "Horas Normales Trabajadas", slip.hours_normal, force_create=True)
                    slip._sync_input_line("HS_EXT50", "Horas Extras 50%", slip.hours_ext50 or 0.0, force_create=True)
                    slip._sync_input_line("HS_EXT100", "Horas Extras 100%", slip.hours_ext100 or 0.0, force_create=True)
                else:
                    norm_line = slip.input_line_ids.filtered(lambda i: i.code == "HS_NORM")
                    if not norm_line:
                        slip._sync_input_line("HS_NORM", "Horas Normales Trabajadas", slip.hours_normal, force_create=True)
                    ext50_line = slip.input_line_ids.filtered(lambda i: i.code == "HS_EXT50")
                    if not ext50_line:
                        slip._sync_input_line("HS_EXT50", "Horas Extras 50%", 0.0, force_create=True)
                    ext100_line = slip.input_line_ids.filtered(lambda i: i.code == "HS_EXT100")
                    if not ext100_line:
                        slip._sync_input_line("HS_EXT100", "Horas Extras 100%", 0.0, force_create=True)

                # Sincronizar worked_days WORK100
                work100 = slip.worked_days_line_ids.filtered(lambda w: w.code == "WORK100")
                if work100:
                    work100[0].number_of_hours = slip.hours_normal
                    if contract.resource_calendar_id and contract.resource_calendar_id.hours_per_day:
                        work100[0].number_of_days = round(
                            slip.hours_normal / contract.resource_calendar_id.hours_per_day, 2
                        )
            else:
                data = slip._resolve_liquidation_days()
                slip.hours_theoretical = 0.0
                slip.hours_leaves = 0.0
                slip.hours_normal = 0.0
                slip.hours_ext50 = 0.0
                slip.hours_ext100 = 0.0
                slip.total_hours_worked = 0.0
                slip.hours_source = ""

                slip.days_theoretical = data["days_theoretical"]
                slip.total_days_vacation = data["total_days_vacation"]
                slip.total_days_worked = data["total_days_worked"]
                slip.days_source = data["source"]
                slip.vacation_source = data["vac_source"]

                # Sincronizar worked_days WORK100
                work100 = slip.worked_days_line_ids.filtered(lambda w: w.code == "WORK100")
                if work100:
                    work100[0].number_of_days = slip.total_days_worked
                    cal = contract.resource_calendar_id
                    h_per_day = cal.hours_per_day if cal and cal.hours_per_day else 8.0
                    work100[0].number_of_hours = round(slip.total_days_worked * h_per_day, 2)

            # Vacaciones: sincronizar input y worked_days si aplica
            vac_days = slip.total_days_vacation
            if vac_days > 0:
                slip._sync_input_line("VAC_DIAS", "Días de Vacaciones Gozadas", vac_days)
                vac_wd = slip.worked_days_line_ids.filtered(lambda w: w.code == "VAC")
                if vac_wd:
                    vac_wd[0].number_of_days = vac_days

            # SIRADIG: Si el empleado tiene deducciones de F.572 cargadas y no existe input manual, inicializar DED_SIRADIG
            emp_siradig = slip.employee_id.ganancias_otras_deducciones_mensual if slip.employee_id else 0.0
            if emp_siradig > 0:
                siradig_line = slip.input_line_ids.filtered(lambda i: i.code == "DED_SIRADIG")
                if not siradig_line:
                    slip._sync_input_line("DED_SIRADIG", "Deducciones Generales SIRADIG F.572 ($)", emp_siradig, force_create=True)

    # ══════════════════════════════════════════════
    # CRUD
    # ══════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("employee_id"):
                emp = self.env["hr.employee"].browse(vals["employee_id"])
                contract = emp.current_version_id or emp.version_id or (emp.version_ids and emp.version_ids[0])
                if contract:
                    if not vals.get("contract_id"):
                        vals["contract_id"] = contract.id

                    # Asignar estructura según el lote si existe y es especializado (Vacaciones, SAC, Liquidación Final)
                    run_id = vals.get("payslip_run_id")
                    run = self.env["hr.payslip.run"].browse(run_id) if run_id else None
                    tipo_liq = run.tipo_liquidacion if run else None
                    if tipo_liq in ("Vacaciones", "SAC", "Liquidación Final"):
                        specialized_struct = self.env["hr.version"]._get_default_struct(
                            contract.wage_type or "monthly", tipo_liquidacion=tipo_liq
                        )
                        if specialized_struct:
                            vals["struct_id"] = specialized_struct.id
                    elif not vals.get("struct_id") and contract.struct_id:
                        vals["struct_id"] = contract.struct_id.id
                    if "input_line_ids" in vals:
                        fixed_inputs = []
                        for cmd in vals["input_line_ids"]:
                            if cmd[0] == 0:
                                line_vals = dict(cmd[2])
                                if not line_vals.get("contract_id"):
                                    line_vals["contract_id"] = contract.id
                                fixed_inputs.append((0, 0, line_vals))
                            else:
                                fixed_inputs.append(cmd)
                        vals["input_line_ids"] = fixed_inputs
        return super().create(vals_list)

    # ══════════════════════════════════════════════
    # VACACIONES — Detección desde hr_holidays (F3.3)
    # ══════════════════════════════════════════════

    def _get_vacation_days_from_leaves(self):
        """Calcula días de vacaciones aprobadas en el período del recibo.

        Detecta vacaciones por:
        1. Tipo de ausencia con XML ID 'payroll_arg.holiday_status_vacaciones_lct'
        2. Código del tipo de ausencia: 'VAC' o 'VACACIONES'
        3. Nombre del tipo de ausencia conteniendo 'vacac' o 'vacat'

        NOTA: No silencia errores. Si la búsqueda falla, se loguea y retorna 0.
        """
        self.ensure_one()
        if not self.employee_id or not self.date_from or not self.date_to:
            return 0.0

        from odoo.fields import Datetime
        dt_from = Datetime.to_datetime(self.date_from)
        dt_to = Datetime.to_datetime(self.date_to).replace(hour=23, minute=59, second=59)

        leaves = self.env["hr.leave"].search([
            ("employee_id", "=", self.employee_id.id),
            ("state", "=", "validate"),
            ("date_from", "<=", dt_to),
            ("date_to", ">=", dt_from),
        ])

        if not leaves:
            return 0.0

        ref_type = self.env.ref("payroll_arg.holiday_status_vacaciones_lct", raise_if_not_found=False)

        vacation_leaves = leaves.filtered(
            lambda l: (ref_type and l.holiday_status_id == ref_type)
            or (hasattr(l.holiday_status_id, "code") and l.holiday_status_id.code in ["VAC", "VACACIONES"])
            or any(term in (l.holiday_status_id.name or "").lower() for term in ["vacaci", "vacat"])
        )

        if not vacation_leaves:
            return 0.0

        total_days = 0.0
        for l in vacation_leaves:
            start = max(l.date_from.date(), self.date_from)
            end = min(l.date_to.date(), self.date_to)
            if end >= start:
                total_days += (end - start).days + 1
        return float(total_days)

    # ══════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════

    def _remove_input_line(self, code):
        """Elimina líneas de input de forma segura tanto para registros guardados como NewId en memoria."""
        to_del = self.input_line_ids.filtered(lambda i: i.code == code)
        if to_del:
            real_recs = to_del.filtered(lambda r: r.id and isinstance(r.id, int))
            if real_recs:
                real_recs.unlink()
            self.input_line_ids = self.input_line_ids - to_del

    def _sync_input_line(self, code, name, amount, force_create=False):
        """Sincroniza una línea de input: actualiza si existe, crea si amount > 0 o force_create, deduplica de forma segura."""
        inp = self.input_line_ids.filtered(lambda i: i.code == code)
        if inp:
            inp[0].amount = amount
            if len(inp) > 1:
                duplicates = inp[1:]
                real_recs = duplicates.filtered(lambda r: r.id and isinstance(r.id, int))
                if real_recs:
                    real_recs.unlink()
                self.input_line_ids = self.input_line_ids - duplicates
        elif amount > 0 or force_create:
            vals = {
                "name": name,
                "code": code,
                "amount": amount,
                "contract_id": self.contract_id.id if self.contract_id else False,
            }
            if self.id and isinstance(self.id, int):
                vals["payslip_id"] = self.id
                self.env["hr.payslip.input"].create(vals)
                self.invalidate_recordset(["input_line_ids"])
            else:
                self.input_line_ids += self.input_line_ids.new(vals)

    @api.depends("payslip_run_id.tipo_liquidacion", "contract_id.wage_type", "struct_id")
    def _compute_is_quincenal(self):
        hourly_types = ("1° Quincena", "2° Quincena", "Quincenal")
        for slip in self:
            if slip.payslip_run_id and slip.payslip_run_id.tipo_liquidacion:
                slip.is_quincenal = (
                    slip.payslip_run_id.tipo_liquidacion in hourly_types
                    or "Quincena" in slip.payslip_run_id.tipo_liquidacion
                )
            elif slip.contract_id and slip.contract_id.wage_type == "hourly":
                slip.is_quincenal = True
            elif slip.struct_id and ("jornal" in (slip.struct_id.code or "").lower() or "quincen" in (slip.struct_id.name or "").lower()):
                slip.is_quincenal = True
            else:
                slip.is_quincenal = False

    def _get_calendar_public_holidays_count(self, cal, date_from, date_to):
        """Calcula la cantidad de feriados públicos en el calendario dentro del período."""
        if not cal or not date_from or not date_to:
            return 0.0
        try:
            tz = pytz.timezone(cal.tz or self.employee_id.tz or "America/Argentina/Cordoba")
            dt_from = tz.localize(datetime.combine(date_from, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
            dt_to = tz.localize(datetime.combine(date_to, time.max)).astimezone(pytz.utc).replace(tzinfo=None)
            leaves = self.env["resource.calendar.leaves"].search([
                ("resource_id", "=", False),
                ("date_from", "<=", dt_to),
                ("date_to", ">=", dt_from),
                "|",
                ("calendar_id", "=", cal.id),
                ("calendar_id", "=", False),
            ])
            holiday_days = set()
            for leaf in leaves:
                l_start = pytz.utc.localize(leaf.date_from).astimezone(tz).date()
                l_end = pytz.utc.localize(leaf.date_to).astimezone(tz).date()
                curr = max(date_from, l_start)
                end_d = min(date_to, l_end)
                while curr <= end_d:
                    day_of_week = str(curr.weekday())
                    if any(att.dayofweek == day_of_week for att in cal.attendance_ids):
                        holiday_days.add(curr)
                    curr += relativedelta(days=1)
            return float(len(holiday_days))
        except Exception as e:
            _logger.warning("Error computando feriados de calendario: %s", e)
            return 0.0

    @api.depends("payslip_run_id.cant_feriados", "contract_id", "date_from", "date_to")
    def _compute_cant_feriados(self):
        for slip in self:
            if slip.feriados_manual:
                continue
            if slip.payslip_run_id and slip.payslip_run_id.cant_feriados > 0:
                slip.cant_feriados = slip.payslip_run_id.cant_feriados
            elif slip.contract_id and slip.contract_id.wage_type == "hourly":
                cal = slip.contract_id.resource_calendar_id
                holiday_days = slip._get_calendar_public_holidays_count(cal, slip.date_from, slip.date_to)
                hours_per_day = cal.hours_per_day if (cal and cal.hours_per_day) else 8.8
                slip.cant_feriados = round(holiday_days * hours_per_day, 2)
            else:
                slip.cant_feriados = 0.0

    @api.onchange("cant_feriados")
    def _onchange_cant_feriados(self):
        for slip in self:
            slip.feriados_manual = True

    @api.depends("payslip_run_id.monto_gratif_no_rem")
    def _compute_monto_gratif_no_rem(self):
        for slip in self:
            if slip.gratif_no_rem_manual:
                continue
            if slip.payslip_run_id:
                slip.monto_gratif_no_rem = slip.payslip_run_id.monto_gratif_no_rem
            else:
                slip.monto_gratif_no_rem = 0.0

    @api.onchange("monto_gratif_no_rem")
    def _onchange_monto_gratif_no_rem(self):
        for slip in self:
            slip.gratif_no_rem_manual = True

    @api.depends("payslip_run_id.monto_compens_no_rem")
    def _compute_monto_compens_no_rem(self):
        for slip in self:
            if slip.compens_no_rem_manual:
                continue
            if slip.payslip_run_id:
                slip.monto_compens_no_rem = slip.payslip_run_id.monto_compens_no_rem
            else:
                slip.monto_compens_no_rem = 0.0

    @api.onchange("monto_compens_no_rem")
    def _onchange_monto_compens_no_rem(self):
        for slip in self:
            slip.compens_no_rem_manual = True

    @api.depends("payslip_run_id.precio_vianda")
    def _compute_precio_vianda(self):
        for slip in self:
            if slip.precio_vianda_manual:
                continue
            if slip.payslip_run_id and slip.payslip_run_id.precio_vianda > 0:
                slip.precio_vianda = slip.payslip_run_id.precio_vianda
            elif not slip.precio_vianda:
                slip.precio_vianda = 0.0

    @api.onchange("precio_vianda")
    def _onchange_precio_vianda(self):
        for slip in self:
            slip.precio_vianda_manual = True

    def _get_antiguedad_start_date(self):
        self.ensure_one()
        contract = self.contract_id
        emp = self.employee_id
        return (
            (contract and (contract.contract_date_start or contract.date_start))
            or (emp and (emp.contract_date_start or emp.first_contract_date))
            or (contract and contract.date_version)
            or False
        )

    @api.depends("antiguedad_override", "antiguedad_anios_manual", "contract_id", "employee_id", "date_to")
    def _compute_antiguedad_anios(self):
        for slip in self:
            if slip.antiguedad_override:
                slip.antiguedad_anios = slip.antiguedad_anios_manual
                continue
            start_date = slip._get_antiguedad_start_date() if (slip.contract_id or slip.employee_id) else False
            if start_date and slip.date_to:
                slip.antiguedad_anios = max(0, slip.date_to.year - start_date.year)
            else:
                slip.antiguedad_anios = 0

    @api.depends("payslip_run_id.coef_contrib_ss", "payslip_run_id.coef_contrib_os", "company_id")
    def _compute_coef_contrib(self):
        for slip in self:
            src = slip.payslip_run_id or slip.company_id
            slip.coef_contrib_ss = src.coef_contrib_ss
            slip.coef_contrib_os = src.coef_contrib_os

    def _sync_variable_concepts(self):
        """Sincroniza los conceptos variables (PREMIO_PROD, PRESENTISMO, PORTITULO, OBJETIVOS, FERIADO, GRATIF, COMPENS)
        desde los toggles/montos del recibo y del lote hacia input_line_ids solo si es quincenal."""
        for slip in self:
            if not slip.is_quincenal:
                continue
            run = slip.payslip_run_id
            if run and run.is_quincenal:
                pp_amt = run.monto_premio_produccion if slip.premio_prod_ok else 0.0
                slip._sync_input_line("PREMIO_PROD", "Premio Producción", pp_amt)

                pres_amt = run.monto_presentismo if slip.presentismo_ok else 0.0
                slip._sync_input_line("PRESENTISMO", "Presentismo", pres_amt)

                port_amt = run.monto_portitulo if slip.portitulo_ok else 0.0
                slip._sync_input_line("PORTITULO", "Portítulo", port_amt)

            if slip.monto_objetivos > 0 or (run and run.is_quincenal):
                obj_amt = slip.monto_objetivos if slip.monto_objetivos > 0 else 0.0
                slip._sync_input_line("OBJETIVOS", "Objetivos", obj_amt)

            # Feriados (en horas)
            fer_amt = slip.cant_feriados if (slip.cant_feriados and slip.cant_feriados > 0) else 0.0
            slip._sync_input_line("FERIADO", "Feriados (Hs)", fer_amt)

            # Conceptos No Remunerativos: aplican si están activos
            gratif_val = slip.monto_gratif_no_rem if slip.gratif_no_rem_ok else 0.0
            slip._sync_input_line("GRATIF_NO_REM", "Gratif. Extraordinaria No Rem.", gratif_val)

            comp_val = slip.monto_compens_no_rem if slip.compens_no_rem_ok else 0.0
            slip._sync_input_line("COMPENS_NO_REM", "Compens. Extraord. NR", comp_val)

            # Viandas (en unidades / cant_viandas)
            viandas_qty = slip.cant_viandas if (slip.cant_viandas and slip.cant_viandas > 0) else 0.0
            slip._sync_input_line("DESC_VIANDAS", "Descuento Viandas", viandas_qty)

            # Aporte Adicional Seg. Social (Monto fijo si está en 2da quincena)
            is_q2 = (slip.tipo_liquidacion == "2° Quincena") or (run and run.tipo_liquidacion == "2° Quincena")
            adic_ss_monto = (slip.employee_id.aporte_adicional_ss_monto or 0.0) if is_q2 else 0.0
            slip._sync_input_line("APORTE_ADIC_SS", "Aporte Adicional Seg. Social", adic_ss_monto)

    # ══════════════════════════════════════════════
    # ONCHANGES (F8.1 — Descompuesto en métodos atómicos)
    # ══════════════════════════════════════════════

    @api.onchange("input_line_ids")
    def _onchange_input_line_ids(self):
        for slip in self:
            if slip.contract_id and slip.contract_id.wage_type == "hourly":
                slip._sync_liquidation_summary(force_external=False)

    @api.onchange("total_days_vacation", "total_days_worked")
    def _onchange_liquidation_days_units(self):
        for slip in self:
            if slip.contract_id and slip.contract_id.wage_type != "hourly":
                slip._sync_liquidation_summary()

    @api.onchange("struct_id")
    def onchange_struct_id(self):
        for slip in self:
            input_lines = slip.input_line_ids.browse([])
            input_line_ids = slip.get_inputs(
                slip.contract_id, slip.date_from, slip.date_to
            )
            for line in input_line_ids:
                input_lines += input_lines.new(line)
            slip.input_line_ids = input_lines
            slip._sync_liquidation_summary(force_external=True)

    def _clear_all_data(self):
        """Limpia todos los datos del payslip cuando se deselecciona el empleado."""
        self.contract_id = False
        self.struct_id = False
        self.worked_days_line_ids = [(5, 0, 0)]
        self.input_line_ids = [(5, 0, 0)]
        self.line_ids = [(5, 0, 0)]

    def _resolve_contract(self):
        """Resuelve el contrato activo del empleado."""
        emp = self.employee_id
        contract = emp.current_version_id or emp.version_id or (emp.version_ids and emp.version_ids[0])
        is_different_employee = self.contract_id and self.contract_id.employee_id != emp
        self.contract_id = contract

        if is_different_employee or not self.worked_days_line_ids:
            self.worked_days_line_ids = [(5, 0, 0)]
            self.input_line_ids = [(5, 0, 0)]
            self.line_ids = [(5, 0, 0)]

    def _resolve_struct(self):
        """Resuelve la estructura salarial desde el lote, empleado o contrato."""
        emp = self.employee_id
        contract = self.contract_id
        wt = emp.wage_type or (contract.wage_type if contract else "monthly")
        tipo_liq = self.payslip_run_id.tipo_liquidacion if self.payslip_run_id else None

        if tipo_liq in ("Vacaciones", "SAC", "Liquidación Final"):
            specialized = self.env["hr.version"]._get_default_struct(wt, tipo_liquidacion=tipo_liq)
            if specialized:
                self.struct_id = specialized
                return

        if emp.struct_id:
            self.struct_id = emp.struct_id
        elif contract and contract.struct_id:
            self.struct_id = contract.struct_id
        else:
            struct = self.env["hr.version"]._get_default_struct(wt, tipo_liquidacion=tipo_liq)
            if struct:
                self.struct_id = struct

    def _sync_period_dates(self):
        """Sincroniza fechas desde el lote si existen y no están configuradas."""
        if self.payslip_run_id:
            if self.payslip_run_id.date_start and not self.date_from:
                self.date_from = self.payslip_run_id.date_start
            if self.payslip_run_id.date_end and not self.date_to:
                self.date_to = self.payslip_run_id.date_end
            return

        if self.date_from and not self.date_to:
            self.date_to = (self.date_from + relativedelta(months=1, day=1, days=-1))

    @api.onchange("employee_id")
    def onchange_employee(self):
        for slip in self:
            if not slip.employee_id:
                slip._clear_all_data()
                continue
            if slip.state and slip.state != "draft":
                continue

            slip._resolve_contract()
            slip._resolve_struct()
            slip._sync_period_dates()

            # Regenerar worked days e inputs
            if slip.contract_id and slip.date_from and slip.date_to:
                slip.onchange_dates()
            if slip.struct_id:
                slip.onchange_struct_id()

            # Cálculo centralizado de horas/días (forzando lectura de datos externos: asistencias/calendario)
            slip._sync_liquidation_summary(force_external=True)

            slip._compute_name()
            slip.company_id = slip.employee_id.company_id

    # ══════════════════════════════════════════════
    # COMPUTE LEAVES / WORKED DAYS
    # ══════════════════════════════════════════════

    def _compute_leave_days(self, contract, day_from, day_to):
        res = super()._compute_leave_days(contract, day_from, day_to)
        fixed_res = []
        for line in res:
            line_dict = dict(line)
            name = (line_dict.get("name") or "").lower()
            code = line_dict.get("code")
            if not code or code == "GLOBAL" or code is False:
                if any(k in name for k in ["vacac", "vacat"]):
                    line_dict["code"] = "VAC"
                    line_dict["name"] = "Licencia por Vacaciones (LCT)"
                elif any(k in name for k in ["enferm", "sick", "illness"]):
                    line_dict["code"] = "ENF"
                else:
                    line_dict["code"] = "LEAVE"
            if line_dict.get("number_of_hours", 0) < 0:
                line_dict["number_of_hours"] = abs(line_dict["number_of_hours"])
            if line_dict.get("number_of_days", 0) < 0:
                line_dict["number_of_days"] = abs(line_dict["number_of_days"])
            fixed_res.append(line_dict)
        return fixed_res

    def _compute_worked_days(self, contract, day_from, day_to):
        attendances = super()._compute_worked_days(contract, day_from, day_to)
        leaves = self._compute_leave_days(contract, day_from, day_to)
        total_leave_hours = sum(
            abs(l.get("number_of_hours", 0.0))
            for l in leaves
            if l.get("code") in ["VAC", "LEAVE", "ENF"]
        )
        if total_leave_hours > 0 and attendances and "number_of_hours" in attendances:
            attendances["number_of_hours"] = max(0.0, attendances["number_of_hours"] - total_leave_hours)
            if contract.resource_calendar_id and contract.resource_calendar_id.hours_per_day:
                attendances["number_of_days"] = round(
                    attendances["number_of_hours"] / contract.resource_calendar_id.hours_per_day, 2
                )
        return attendances

    # ══════════════════════════════════════════════
    # COMPUTE SHEET (F10.1 — con validaciones pre-cómputo)
    # ══════════════════════════════════════════════

    def compute_sheet(self):
        for slip in self:
            # ── Validaciones pre-cómputo (F10.1) ──
            if not slip.contract_id and slip.employee_id:
                contract = (
                    slip.employee_id.current_version_id
                    or slip.employee_id.version_id
                    or (slip.employee_id.version_ids and slip.employee_id.version_ids[0])
                )
                if contract:
                    slip.contract_id = contract
            if not slip.contract_id:
                raise UserError(
                    f"El recibo de '{slip.employee_id.name}' no tiene contrato asignado. "
                    f"Asegúrese de que el empleado tenga un contrato/versión activa."
                )

            if not slip.struct_id:
                slip._resolve_struct()
            if not slip.struct_id:
                raise UserError(
                    f"El recibo de '{slip.employee_id.name}' no tiene estructura salarial. "
                    f"Configure la estructura en el empleado o contrato."
                )

            if not slip.contract_id.wage:
                raise UserError(
                    f"El contrato de '{slip.employee_id.name}' tiene salario básico $0. "
                    f"Configure el sueldo/valor hora antes de liquidar."
                )

            if slip.contract_id and not slip.worked_days_line_ids:
                slip.onchange_dates()

            # ── Cálculo centralizado de horas/días ──
            slip._sync_liquidation_summary()

            # Garantizar que ningún worked_days_line quede con código vacío
            for wdl in slip.worked_days_line_ids:
                if not wdl.code or wdl.code == "GLOBAL":
                    n = (wdl.name or "").lower()
                    wdl.code = "VAC" if any(k in n for k in ["vacac", "vacat"]) else "WORK100"

            # Captura de variables históricas congeladas y base de mes anterior
            slip._capture_historical_snapshots()
            slip._compute_prev_month_gross()
            slip._sync_variable_concepts()

            if slip.contract_id:
                for line in slip.input_line_ids:
                    if not line.contract_id:
                        line.contract_id = slip.contract_id.id

        res = super().compute_sheet()
        self._compute_totals_arg()
        for slip in self:
            slip._compute_base_imponible_seg_social()
            slip._compute_ganancias_fields()
        return res

    # ══════════════════════════════════════════════
    # CÓMPUTO DE TOTALES ARG
    # ══════════════════════════════════════════════

    @api.depends("line_ids", "line_ids.total", "line_ids.category_id.code")
    def _compute_totals_arg(self):
        for slip in self:
            rem = 0.0
            no_rem = 0.0
            ret = 0.0
            comp = 0.0
            for line in slip.line_ids:
                cat_code = (line.category_id.code or "").upper()
                if cat_code in ["GROSS", "NET"]:
                    continue
                if cat_code == "COMP":
                    comp += abs(line.total)
                    continue
                tipo = str(line.salary_rule_id.tipo_concepto or "")
                if tipo == "1":
                    rem += line.total
                elif tipo == "2":
                    no_rem += line.total
                elif tipo == "3":
                    ret += abs(line.total)
                elif tipo == "4":
                    comp += abs(line.total)
            slip.total_remunerativo = round(rem, 2)
            slip.total_no_remunerativo = round(no_rem, 2)
            slip.total_retenciones = round(ret, 2)
            slip.total_contribuciones = round(comp, 2)
            slip.neto_liquidacion = round(rem + no_rem - ret, 2)
            slip.costo_total_empleador = round(rem + no_rem + comp, 2)

    @api.depends("line_ids", "line_ids.total", "line_ids.category_id.code")
    def _compute_contribucion_lines(self):
        for slip in self:
            slip.contribucion_line_ids = slip.line_ids.filtered(
                lambda l: (l.category_id.code or "").upper() == "COMP"
            )

    # ══════════════════════════════════════════════
    # AFIP F931
    # ══════════════════════════════════════════════

    def _get_afip_info_f931(self):
        self.ensure_one()
        employee = self.employee_id
        contract = self.contract_id
        company = self.company_id

        sueldo_val = 0.0
        hs_extras_val = 0.0
        vacaciones_val = 0.0
        sac_val = 0.0
        hs_extras_cant = 0

        for line in self.line_ids:
            rule_code = (line.code or "").upper()
            if "VAC" in rule_code:
                vacaciones_val += line.total
            elif "EXT" in rule_code or "HS_EXT" in rule_code:
                hs_extras_val += line.total
                hs_extras_cant += int(line.quantity or 0)
            elif "SAC" in rule_code or "AGUIN" in rule_code:
                sac_val += line.total
            elif line.salary_rule_id.tipo_concepto == "1":
                sueldo_val += line.total

        total_rem = self.total_remunerativo
        total_norem = self.total_no_remunerativo

        is_jornal = contract.wage_type == "hourly"
        if is_jornal:
            k_dias = 0.0
            k_horas = int(self.total_hours_worked or 0)
        else:
            k_dias = float(self.total_days_worked or DIAS_BASE_MENSUAL_LCT)
            k_horas = 0

        info_f931 = {
            "fijos": {
                "cuil": employee.cuil or "20000000000",
                "nombre_completo": employee.name or "",
                "conyuge": 1 if employee.marital == "married" else 0,
                "hijos": int(employee.children or 0),
                "condicion": contract.afip_condition_id.code or "01",
                "actividad": contract.afip_activity_id.code or "049",
                "obra_social": employee.health_insurance_id.code or "126205",
                "adherentes": int(employee.health_insurance_adherents or 0),
                "zona": contract.afip_zone_id.code or "18",
                "localidad": employee.workplace_location or "Córdoba",
                "modalidad_contrato": contract.afip_contract_type_id.code or "001",
                "porc_contr_dif_ss": contract.diff_task_contrib_percent or 0.0,
                "seguro_vida_obligatorio": 1 if contract.has_mandatory_life_insurance else 0,
                "tipo_empresa": company.afip_company_type or "1",
                "convencionado": 1 if contract.is_convencionado else 0,
                "porcentaje_aporte_adicional_ss": contract.additional_ss_contrib_percent or 0.0,
                "corresponde_reduccion": 1 if contract.has_reduction else 0,
                "regimen": 1,
                "tipo_operacion": 0,
                "forma_pago": employee.payment_type or "3",
                "cbu": employee.cbu or "",
                "area": employee.department_id.name or "Administración",
            },
            "variables": {
                "cuil": employee.cuil or "20000000000",
                "situacion": int(contract.afip_situation_id.code or 1),
                "situacion_1": int(contract.afip_situation_id.code or 1),
                "dia_sr1": 1,
                "situacion_2": 1,
                "dia_sr2": 1,
                "situacion_3": 1,
                "dia_sr3": 1,
                "codigo_siniestrado": int(contract.afip_siniestrado_id.code or 0),
            },
            "importes": {
                "cuil": employee.cuil or "20000000000",
                "aporte_vol": 0,
                "asign_fam": 0,
                "capital_lrt": 0,
                "rectificacion": 0,
                "incremento": 0,
                "imp_exc_ap_os": 0,
                "imp_exc_ap_ss": 0,
                "remuneracion_total": total_rem,
                "no_remunerativo": total_norem,
                "remuneracion_01": total_rem,
                "remuneracion_02": total_rem,
                "remuneracion_03": total_rem,
                "remuneracion_04": total_rem,
                "remuneracion_05": total_rem,
                "remuneracion_06": 0,
                "remuneracion_07": 0,
                "remuneracion_08": total_rem,
                "remuneracion_09": total_rem,
                "remuneracion_10": total_rem,
                "remuneracion_11": 0,
                "sueldo": sueldo_val,
                "adicionales": 0,
                "premios": 0,
                "hs_extras": hs_extras_val,
                "sac": sac_val,
                "zona_desfavorable": 0,
                "vacaciones": vacaciones_val,
                "maternidad": 0,
                "k_dias": k_dias,
                "k_horas": k_horas,
                "k_hs_extras": hs_extras_cant,
                "aporte_adicional_os": 0,
                "importe_adicional_os": contract.additional_health_insurance_amount or 0,
                "base_diferencial_aos": 0,
                "base_diferencial_cos": 0,
                "base_calculo_diferencial_lrt": 0,
                "base_calculo_diferencial_aporte_ss": 0,
                "base_calculo_diferencial_contribucion_ss": 0,
                "detraccion": 0,
            },
        }
        return info_f931

    def _get_conceptos_liquidados_lsd(self):
        self.ensure_one()
        conceptos = []
        for line in self.line_ids:
            cat_code = (line.category_id.code or "").upper()
            if cat_code in ["GROSS", "NET", "COMP"] or line.total == 0:
                continue

            tipo = line.salary_rule_id.tipo_concepto
            importe = line.total if tipo != "3" else -abs(line.total)
            cod_con = (line.salary_rule_id.afip_code or line.code or "CONC")[:10]
            unidades = line.salary_rule_id.afip_unit or ("H" if self.contract_id.wage_type == "hourly" else "D")

            conceptos.append(
                {
                    "concepto": cod_con,
                    "cantidad": float(line.quantity or 1.0),
                    "importe": round(importe, 2),
                    "unidades": unidades,
                }
            )
        return conceptos

    # ══════════════════════════════════════════════
    # RECIBO DICT (F5.1 — contribuciones desde res.company)
    # ══════════════════════════════════════════════

    def _to_recibo_dict(self, nro_liq=1, tipo_liq="Mensual"):
        self.ensure_one()
        emp = self.employee_id
        company = self.company_id
        contract = self.contract_id

        # ── Datos de empresa ──
        domicilio = {
            "pk": company.id,
            "calle": company.street or "Calle Principal",
            "numero": company.street2 or "100",
            "piso": None,
            "oficina": None,
            "barrio": None,
            "localidad": {
                "pk": 1,
                "provincia": {
                    "pk": 1,
                    "name": company.state_id.name or "Córdoba",
                    "pais": {"pk": 1, "code": "AR", "name": "Argentina"},
                },
                "name": company.city or "Córdoba",
                "text": company.city or "Córdoba",
            },
            "cod_postal": company.zip or "5000",
        }

        ultimo_pago_ss = {
            "id": 1,
            "banco": company.last_ss_bank_id.name or "Banco Nación",
            "mes": company.last_ss_month or 1,
            "anio": company.last_ss_year or datetime.today().year,
            "fecha_pago": str(company.last_ss_payment_date or datetime.today().date()),
            "empresa": company.id,
        }

        # ── Conceptos del recibo (100% trazables desde line_ids calculadas) ──
        conceptos_recibo = []
        orden = 1
        for line in self.line_ids:
            cat_code = (line.category_id.code or "").upper()
            if cat_code in ["GROSS", "NET"] or line.total == 0:
                continue

            tipo = int(line.salary_rule_id.tipo_concepto or ("4" if cat_code == "COMP" else "1"))
            code = "INSSJP" if line.code == "RET_INSSJP" else (line.code or "")
            line_name = line.name or ""
            # Si se aplicó tope a la retención, visibilizar la base en el nombre
            if line.code in ("RET_JUB", "RET_INSSJP", "RET_OS") and self.is_tope_applied and self.base_imponible_seg_social > 0:
                line_name = f"{line.name} [Tope: ${self.base_imponible_seg_social:,.2f}]"

            if line.salary_rule_id.afip_unit == "%" or (line.rate and line.rate not in (0.0, 100.0)):
                cant = float(line.rate)
            else:
                cant = float(line.quantity or 1.0)
            if cat_code == "COMP":
                tipo = 4
                if line.code == "COMP_SCVO":
                    cant = 0.0

            conceptos_recibo.append(
                {
                    "code": code,
                    "name": line_name,
                    "tipo_concepto": tipo,
                    "concepto": {
                        "code": code,
                        "tipo_concepto": tipo,
                        "name": line_name,
                    },
                    "orden": orden,
                    "cantidad": cant,
                    "importe": round(abs(line.total), 2),
                }
            )
            orden += 1

        rem = self.total_remunerativo
        no_rem = self.total_no_remunerativo
        ret = self.total_retenciones
        neto = self.neto_liquidacion

        # ── Aportes del Trabajador (estrictamente desde líneas calculadas, cero constantes) ──
        line_jub = self.line_ids.filtered(lambda l: l.code == "RET_JUB")
        line_inssjp = self.line_ids.filtered(lambda l: l.code in ["RET_INSSJP", "INSSJP"])
        line_os = self.line_ids.filtered(lambda l: l.code == "RET_OS")
        line_sind = self.line_ids.filtered(lambda l: l.code == "RET_SIND")

        ap_jub_val = abs(line_jub[0].total) if line_jub else 0.0
        ap_inssjp_val = abs(line_inssjp[0].total) if line_inssjp else 0.0
        ap_ss_val = round(ap_jub_val + ap_inssjp_val, 2)
        ap_os_val = abs(line_os[0].total) if line_os else 0.0
        ap_sin_val = abs(line_sind[0].total) if line_sind else 0.0

        # ── Contribuciones Patronales (estrictamente desde líneas calculadas, cero constantes) ──
        line_ct_art = self.line_ids.filtered(lambda l: l.code in ["COMP_ART", "CTRART"])
        line_ct_jub = self.line_ids.filtered(lambda l: l.code in ["COMP_JUB", "CTJUBI"])
        line_ct_os = self.line_ids.filtered(lambda l: l.code in ["COMP_OS", "CTOBSO"])
        line_ct_aaff = self.line_ids.filtered(lambda l: l.code in ["COMP_AAFF", "CTASFA"])
        line_ct_fne = self.line_ids.filtered(lambda l: l.code in ["COMP_FNE", "CTRFNE"])
        line_ct_inssjp = self.line_ids.filtered(lambda l: l.code in ["COMP_INSSJP", "CTINSS"])
        line_ct_scvo = self.line_ids.filtered(lambda l: l.code in ["COMP_SCVO", "SEGOBL"])
        line_ct_uom = self.line_ids.filtered(lambda l: l.code in ["COMP_UOM_VIDA", "SEGUOM"])

        ct_jub_val = abs(line_ct_jub[0].total) if line_ct_jub else 0.0
        ct_inssjp_val = abs(line_ct_inssjp[0].total) if line_ct_inssjp else 0.0
        ct_aaff_val = abs(line_ct_aaff[0].total) if line_ct_aaff else 0.0
        ct_fne_val = abs(line_ct_fne[0].total) if line_ct_fne else 0.0
        ct_os_val = abs(line_ct_os[0].total) if line_ct_os else 0.0
        ct_art_val = abs(line_ct_art[0].total) if line_ct_art else 0.0
        ct_scvo_val = abs(line_ct_scvo[0].total) if line_ct_scvo else 0.0
        ct_uom_val = abs(line_ct_uom[0].total) if line_ct_uom else 0.0

        # CT_SS = Total Seguridad Social Patronal (Jubilación + Ley 19032 + AAFF + FNE)
        # Nota: en recibo_4.py se computa: ct_ss = main_agrupadores['CT_SS'] - ct_inssjp
        # Por ende ct_ss queda exactamente: ct_jub + ct_aaff + ct_fne
        ct_ss_val = round(ct_jub_val + ct_inssjp_val + ct_aaff_val + ct_fne_val, 2)

        # ── Detalle de la Composición Salarial (Pie de página individual según normativa AFIP F.931) ──
        # La composición del pie de página se calcula sobre el Bruto del mes actual de este empleado (rem),
        # aplicando el desdoblamiento del 15% a ANSSAL (FSR) que AFIP agrupa en Seguridad Social en el F.931.

        # 1. Costo Sindical:
        pie_ap_sin = abs(line_sind[0].total) if line_sind else round(rem * 0.025, 2)
        pie_ct_sin = 0.0

        # 2. INSSJP (PAMI):
        pie_ap_inssjp = abs(line_inssjp[0].total) if line_inssjp else round(rem * (company.inssjp_contrib_rate or 3.0) / 100.0, 2)
        coef_ss = self.coef_contrib_ss if self.coef_contrib_ss else ((self.payslip_run_id and self.payslip_run_id.coef_contrib_ss) or company.coef_contrib_ss or 1.0)
        pie_ct_inssjp = round(rem * ((company.inssjp_patronal_rate or 1.59) / 100.0) * coef_ss, 2)

        # 3. ART:
        art_pct = (company.art_variable_rate or 5.82) / 100.0
        pie_art = round(rem * art_pct, 2)

        # 4. SCVO:
        pie_svida = abs(line_ct_scvo[0].total) if line_ct_scvo else 424.62

        # 5. Obra Social (desglose 85% OS y 15% ANSSAL según F.931):
        base_os = round(rem + no_rem, 2)
        tot_ap_os = abs(line_os[0].total) if line_os else round(base_os * (company.os_worker_rate or 3.0) / 100.0, 2)
        pie_ap_os = round(tot_ap_os * 0.85, 2)
        anssal_ap = round(tot_ap_os * 0.15, 2)

        os_pat_rate = (company.os_patronal_rate or 6.0) / 100.0
        pie_ct_os = round(base_os * (os_pat_rate * 0.85), 2)
        anssal_ct = round(base_os * (os_pat_rate * 0.15), 2)
        anssal_total = round(anssal_ct + anssal_ap, 2)

        # 6. Seguridad Social (clasificación de ANSSAL dentro de Seguridad Social según F.931):
        # Aportes Trabajador: Jubilación 11% + ANSSAL 0,45%
        pie_ap_jub = abs(line_jub[0].total) if line_jub else round(rem * 0.11, 2)
        is_q2 = (self.tipo_liquidacion == "2° Quincena") or (self.payslip_run_id and self.payslip_run_id.tipo_liquidacion == "2° Quincena")
        pie_ap_ss = round(rem * 0.11 + anssal_ap, 2) if is_q2 else round(pie_ap_jub + anssal_ap, 2)

        # Contribuciones Patronales: suma de líneas individuales redondeadas (SIPA + AAFF + FNE con coef) + ANSSAL
        sipa_rate = (company.jubilacion_patronal_rate or 10.77) / 100.0
        aaff_rate = (company.aaff_patronal_rate or 4.70) / 100.0
        fne_rate = (company.fne_patronal_rate or 0.94) / 100.0
        ct_jub_ind = round(rem * sipa_rate * coef_ss, 2)
        ct_aaff_ind = round(rem * aaff_rate * coef_ss, 2)
        ct_fne_ind = round(rem * fne_rate * coef_ss, 2)
        pie_ct_ss_base = round(ct_jub_ind + ct_aaff_ind + ct_fne_ind, 2)
        if is_q2:
            pie_ct_ss = round(pie_ct_ss_base + anssal_total, 2)
        else:
            pie_ct_ss = round(pie_ct_ss_base + anssal_ap, 2)

        total_contrib = round(self.total_contribuciones or (ct_art_val + ct_jub_val + ct_os_val + ct_aaff_val + ct_fne_val + ct_inssjp_val + ct_scvo_val + ct_uom_val), 2)
        costo_total = round(self.costo_total_empleador or (rem + no_rem + total_contrib), 2)

        periodo_str = self.date_from.strftime("%Y-%m") if self.date_from else datetime.today().strftime("%Y-%m")
        fecha_pago_str = str(self.payment_date or self.date_to or (self.payslip_run_id and self.payslip_run_id.payment_date) or datetime.today().date())

        basico_mostrado = contract.wage if contract else 0.0

        return {
            "empresa": {
                "pk": company.id,
                "name": company.name or "",
                "cuit": company.cuit or company.vat or "20123456780",
                "domicilio": domicilio,
                "ultimo_pago_seguridad_social": ultimo_pago_ss,
            },
            "liquidacion": {
                "nro_liq": nro_liq,
                "tipo_liquidacion": tipo_liq,
                "periodo": {"periodo": periodo_str},
                "fecha_pago": fecha_pago_str,
            },
            "empleado": {
                "legajo": emp.legajo or emp.id,
                "first_name": emp.name or "",
                "last_name": "",
                "cuil": emp.cuil or "20000000000",
                "fecha_ingreso": str(contract.date_start or "2020-01-01"),
                "fecha_ingreso_2": None,
                "categoria": emp.labor_category_id.name or "Operario",
                "contrato": contract.afip_contract_type_id.name or "Tiempo Indeterminado",
                "obra_social": emp.health_insurance_id.name or "O.S. General",
                "area": emp.department_id.name or "Producción",
                "posicion": emp.job_title or "Operario",
                "basico": basico_mostrado,
                "lugar_trabajo": emp.workplace_location or "Córdoba",
                "relacion_bancaria": {
                    "forma_pago": "CBU" if emp.payment_type == "3" else "EFVO",
                    "numero_cuenta": None,
                    "cbu": emp.cbu or None,
                },
            },
            "conceptos_liquidados": conceptos_recibo,
            "totales_liquidacion": {
                "total_remunerativo": round(rem, 2),
                "total_no_remunerativo": round(no_rem, 2),
                "total_retenciones": round(ret, 2),
                "neto_liquidacion": round(neto, 2),
                "total_contribuciones": total_contrib,
                "costo_conceptos": costo_total,
                "composicion_salarial": {
                    "ct_sin": pie_ct_sin,
                    "ap_sin": pie_ap_sin,
                    "ct_ss": pie_ct_ss,
                    "ap_ss": pie_ap_ss,
                    "ct_os": pie_ct_os,
                    "ap_os": pie_ap_os,
                    "ct_inssjp": pie_ct_inssjp,
                    "ap_inssjp": pie_ap_inssjp,
                    "art": pie_art,
                    "svida": pie_svida,
                },
                "main_agrupadores": {
                    "AP_SS": round(pie_ap_ss + pie_ap_inssjp, 2),
                    "CT_SS": round(pie_ct_ss + pie_ct_inssjp, 2),
                    "AP_OS": pie_ap_os,
                    "CT_OS": pie_ct_os,
                    "AP_SIN": pie_ap_sin,
                    "CT_SIN": pie_ct_sin,
                },
            },
        }

    def action_print_recibo_pdf(self):
        """Genera y descarga el Recibo de Sueldo oficial en PDF para esta liquidación individual."""
        self.ensure_one()
        if not self.line_ids:
            self.compute_sheet()

        temp_dir = tempfile.mkdtemp()
        try:
            periodo_tag = self.date_from.strftime("%Y%m") if self.date_from else "202601"
            emp_clean = (self.employee_id.name or f"empleado_{self.employee_id.id}").replace(" ", "_")
            filename = f"Recibo_{emp_clean}_{periodo_tag}"

            recibo_payload = [self._to_recibo_dict(
                nro_liq=getattr(self.payslip_run_id, "afip_nro_liquidacion", 1) or 1,
                tipo_liq=getattr(self.payslip_run_id, "tipo_liquidacion", "Mensual") or "Mensual",
            )]

            downloader = ReciboDownloader(
                json_data=recibo_payload,
                output_path=temp_dir,
                filename=filename,
                base_version=4,
            )
            file_path, err = downloader.descargar_recibo()
            if not file_path or err:
                raise UserError(f"Error generando recibo de sueldo: {err}")

            with open(file_path, "rb") as f:
                pdf_bytes = f.read()

            out_name = f"{filename}.pdf"
            attachment = self.env["ir.attachment"].create({
                "name": out_name,
                "type": "binary",
                "datas": base64.b64encode(pdf_bytes),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/pdf",
            })

            return {
                "type": "ir.actions.act_url",
                "url": f"/web/content/{attachment.id}?download=true",
                "target": "self",
            }
        finally:
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception:
                        pass
                try:
                    os.rmdir(root)
                except Exception:
                    pass

    def action_open_export_wizard(self):
        """Abre el asistente de exportación de reportes para este recibo individual."""
        self.ensure_one()
        return {
            "name": "Exportar Recibo de Sueldo",
            "type": "ir.actions.act_window",
            "res_model": "payroll.arg.export.wizard",
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "new",
            "context": {
                "default_payslip_id": self.id,
                "default_payslip_run_id": self.payslip_run_id.id if self.payslip_run_id else False,
            },
        }

    def action_open_payslip(self):
        """Abre la vista formulario del recibo individual."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "res_id": self.id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "current",
        }



class HrPayslipInput(models.Model):
    _inherit = "hr.payslip.input"

    contract_id = fields.Many2one(
        "hr.version",
        string="Contract",
        required=False,
    )


class HrPayslipWorkedDays(models.Model):
    _inherit = "hr.payslip.worked_days"

    code = fields.Char(
        string="Código",
        required=True,
        default="WORK100",
        help="Código de identificación del concepto de días u horas trabajadas/ausencias.",
    )

    @api.onchange("name")
    def _onchange_name(self):
        if not self.code and self.name:
            n = self.name.lower()
            if any(k in n for k in ["vacac", "vacat"]):
                self.code = "VAC"
            elif any(k in n for k in ["enferm", "sick"]):
                self.code = "ENF"
            else:
                self.code = "LEAVE"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                n = (vals.get("name") or "").lower()
                if any(k in n for k in ["vacac", "vacat"]):
                    vals["code"] = "VAC"
                elif any(k in n for k in ["enferm", "sick"]):
                    vals["code"] = "ENF"
                elif "work" in n or "normal" in n:
                    vals["code"] = "WORK100"
                else:
                    vals["code"] = "LEAVE"
        return super().create(vals_list)

    def write(self, vals):
        if "code" in vals and not vals["code"]:
            for rec in self:
                n = (vals.get("name") or rec.name or "").lower()
                if any(k in n for k in ["vacac", "vatat"]):
                    vals["code"] = "VAC"
                elif any(k in n for k in ["enferm", "sick"]):
                    vals["code"] = "ENF"
                else:
                    vals["code"] = "LEAVE"
        return super().write(vals)
