"""@file
Recibo de sueldo argentino (`hr.payslip`): novedades, parámetros de las reglas, Ganancias,
datos para el Libro de Sueldos Digital, el F.931 y el recibo PDF.

Flujo de un recibo (ver docs/flujos.md y docs/liquidacion.md):

1. Al crearse (o al cambiar de estructura) recibe **todas** las entradas de su estructura con el valor
   automático del período (`_prepare_input_lines()`): horas del calendario, feriados, vacaciones
   aprobadas, deducciones SIRADIG y valores fijados en el lote.
2. El usuario corrige las entradas (en el recibo o en la matriz del lote).
3. `compute_sheet()` evalúa las reglas salariales. Las reglas leen las entradas con `inp('CÓDIGO')` y los
   parámetros de la compañía / lote con `payroll.<clave>` (`get_payroll_dict()`); nunca modifican las
   entradas.
4. Los totales argentinos (remunerativo, no remunerativo, retenciones, contribuciones) se calculan
   sumando las líneas según el *Tipo de Concepto AFIP* de su regla (`_compute_totals_arg()`).
5. Las exportaciones leen las líneas calculadas: `_get_afip_info_f931()`,
   `_get_conceptos_liquidados_lsd()` y `_to_recibo_dict()`.
"""
import base64
import calendar
import logging
import os
import tempfile
from datetime import datetime, time

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from py_arg_reports.reporters.recibo_sueldo.base import ReciboDownloader
from .hr_contract import DIAS_BASE_MENSUAL_LCT

_logger = logging.getLogger(__name__)

## Zona horaria por defecto para convertir fechas de licencias y feriados (la planta está en Córdoba).
DEFAULT_TZ = "America/Argentina/Cordoba"
## Tipos de lote quincenales: usan medio tope imponible y la base de contribuciones del mes anterior.
QUINCENA_TYPES = ("1° Quincena", "2° Quincena", "Quincenal")
## Tipos de lote que usan una estructura propia (no la del contrato).
SPECIALIZED_RUN_TYPES = ("Vacaciones", "SAC", "Liquidación Final")
## Parte de Obra Social que va al Fondo Solidario de Redistribución (ANSSAL) en el F.931
ANSSAL_SHARE = 0.15
## Conceptos que el F.931 agrupa como "Vacaciones".
F931_VACACIONES_CODES = ("VACACIONES", "VACACIONES_MENSUAL", "VAC_NO_GOZ_MENS", "VAC_NO_GOZ_JORNAL")
## Conceptos que el F.931 agrupa como "Horas extras".
F931_HS_EXTRAS_CODES = ("HS_EXT_50", "HS_EXT_100")
## Conceptos que el F.931 agrupa como "SAC".
F931_SAC_CODES = ("SAC_MENSUAL", "SAC_JORNAL", "SAC_PROP_MENS", "SAC_PROP_JORNAL")


class HrPayslip(models.Model):
    """Recibo de sueldo argentino.

    Las novedades del período (horas, feriados, premios, viandas, etc.) viven
    ÚNICAMENTE en ``input_line_ids``. Las reglas salariales leen ``inp('CODE')``
    y nada más. Los valores automáticos (calendario, licencias, asistencias,
    valores del lote) se cargan en las líneas de entrada cuando nace el recibo
    (``get_inputs``) o a pedido (``action_reload_period_inputs``); el cálculo
    del recibo nunca modifica las entradas.
    """

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

    # ──────────────────────────────────────────────
    # Parámetros por recibo
    # ──────────────────────────────────────────────
    tope_imponible_retenciones = fields.Float(
        string="Tope Imponible Retenciones ($)",
        help="Base imponible máxima para los aportes de Seguridad Social de este recibo. "
             "Vacío = tope de la compañía (la mitad en liquidaciones quincenales).",
    )
    base_imponible_seg_social = fields.Float(
        string="Base Imponible Seg. Social ($)",
        compute="_compute_base_imponible_seg_social",
        store=True,
        help="Base efectivamente usada por la retención de Jubilación.",
    )
    is_tope_applied = fields.Boolean(
        string="Tope Aplicado",
        compute="_compute_base_imponible_seg_social",
        store=True,
    )
    prev_month_gross_manual = fields.Float(
        string="Bruto Mes Anterior Manual ($)",
        help="Base de contribuciones patronales de jornalizados. Si es 0 se toma la suma "
             "remunerativa de los recibos del mes anterior cargados en el sistema.",
    )
    antiguedad_override = fields.Boolean(
        string="Override Antigüedad",
        help="Si se activa, el Adicional Antigüedad usa los años cargados a mano en vez de los "
             "calculados desde la fecha de ingreso.",
    )
    antiguedad_anios_manual = fields.Integer(string="Antigüedad Manual (Años)")
    antiguedad_anios = fields.Integer(
        string="Antigüedad (Años)",
        compute="_compute_antiguedad_anios",
        store=True,
        help="Años de antigüedad cumplidos al cierre del período (override manual o fecha de ingreso).",
    )
    tipo_liquidacion = fields.Selection(
        related="payslip_run_id.tipo_liquidacion",
        string="Tipo de Liquidación",
        readonly=True,
        store=True,
    )
    payment_date = fields.Date(
        string="Fecha de Pago",
        compute="_compute_payment_date",
        store=True,
        readonly=False,
        help="Fecha efectiva de pago. Por defecto la del lote o el fin del período.",
    )

    # ──────────────────────────────────────────────
    # Impuesto a las Ganancias 4ta Categoría
    # ──────────────────────────────────────────────
    ganancias_override = fields.Float(
        string="Override Retención Ganancias ($)",
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

    # ══════════════════════════════════════════════
    # COMPUTES
    # ══════════════════════════════════════════════

    @api.depends("contract_id.wage")
    def _compute_contract_wage(self):
        """Básico del contrato para mostrar en el recibo.

        Sueldo mensual (mensualizados) o valor hora (jornalizados), según `wage_type`.
        """
        for slip in self:
            slip.contract_wage = slip.contract_id.wage

    @api.depends("payslip_run_id.payment_date", "date_to")
    def _compute_payment_date(self):
        """Fecha de pago del recibo (Art. 140 LCT, se imprime en el recibo y va al LSD): la del lote; sin
        lote, el último día del período. Editable a mano."""
        for slip in self:
            slip.payment_date = slip.payslip_run_id.payment_date or slip.date_to or slip.payment_date

    @api.depends("line_ids.amount", "line_ids.code", "total_remunerativo")
    def _compute_base_imponible_seg_social(self):
        """Base imponible de Seguridad Social realmente usada y si se aplicó el tope.

        Se lee de la línea `RET_JUB` (su importe unitario es la base ya topeada); si la regla no está, la
        base es el remunerativo completo. `is_tope_applied` marca los recibos donde el tope imponible
        (Art. 9 Ley 24.241) recortó la base.
        """
        for slip in self:
            jub = slip.line_ids.filtered(lambda l: l.code == "RET_JUB")[:1]
            base = abs(jub.amount) if jub else slip.total_remunerativo
            slip.base_imponible_seg_social = round(base, 2)
            slip.is_tope_applied = bool(jub) and round(base, 2) < round(slip.total_remunerativo, 2)

    @api.depends("line_ids", "line_ids.total", "ganancias_override")
    def _compute_ganancias_fields(self):
        """Resumen de Ganancias del recibo para la vista y los filtros: importe retenido (línea
        `RET_GANANCIAS` o el override manual), si retiene y un texto de estado."""
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

    def _get_antiguedad_start_date(self):
        """Fecha desde la que se cuenta la antigüedad (Art. 18 LCT: tiempo de servicio con el empleador).

        Cascada: inicio del contrato del recibo → inicio de contrato / primer contrato del empleado →
        fecha de la versión del contrato.

        @return date, o False si no hay ninguna fecha cargada.
        """
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
        """Años completos de antigüedad al último día del período: base del Adicional por Antigüedad
        (regla `ADIC_ANTIG`, 1% por año en el CCT UOM 260/75). Con *Override Antigüedad* se usan los
        años cargados a mano (p. ej. antigüedad reconocida de otro empleador del grupo).

        @bug T4 (docs/revision.md): el campo es guardado y no depende de la fecha de ingreso del
             contrato; si esa fecha se corrige, el recibo conserva los años viejos hasta que cambie otra
             dependencia.
        """
        for slip in self:
            if slip.antiguedad_override:
                slip.antiguedad_anios = slip.antiguedad_anios_manual
                continue
            start_date = slip._get_antiguedad_start_date() if (slip.contract_id or slip.employee_id) else False
            if start_date and slip.date_to:
                slip.antiguedad_anios = max(0, relativedelta(slip.date_to, start_date).years)
            else:
                slip.antiguedad_anios = 0

    @api.depends("line_ids", "line_ids.total", "line_ids.category_id.code")
    def _compute_totals_arg(self):
        """Totales argentinos del recibo según el *Tipo de Concepto AFIP* de cada regla.

        - 1 Remunerativo → `total_remunerativo` (sujeto a aportes y contribuciones).
        - 2 No Remunerativo → `total_no_remunerativo`.
        - 3 Retención / Descuento → `total_retenciones` (en positivo).
        - 4 o categoría COMP → `total_contribuciones` (costo del empleador, no afecta el neto).

        Neto = remunerativo + no remunerativo − retenciones. Costo empleador = remunerativo + no
        remunerativo + contribuciones. Se suman los importes **sin redondear** y se redondea el total,
        igual que el recibo oficial (si no, el costo difiere en centavos). Las líneas totalizadoras
        GROSS y NET se ignoran.
        """
        for slip in self:
            rem = 0.0
            no_rem = 0.0
            ret = 0.0
            comp = 0.0
            # Se suman los importes sin redondear (como el recibo oficial) y se redondea el total
            for line in slip.line_ids:
                cat_code = (line.category_id.code or "").upper()
                if cat_code in ["GROSS", "NET"]:
                    continue
                raw = line.amount * line.quantity * line.rate / 100.0
                if cat_code == "COMP":
                    comp += abs(raw)
                    continue
                tipo = str(line.salary_rule_id.tipo_concepto or "")
                if tipo == "1":
                    rem += raw
                elif tipo == "2":
                    no_rem += raw
                elif tipo == "3":
                    ret += abs(raw)
                elif tipo == "4":
                    comp += abs(raw)
            slip.total_remunerativo = round(rem, 2)
            slip.total_no_remunerativo = round(no_rem, 2)
            slip.total_retenciones = round(ret, 2)
            slip.total_contribuciones = round(comp, 2)
            slip.neto_liquidacion = round(rem + no_rem - ret, 2)
            slip.costo_total_empleador = round(rem + no_rem + comp, 2)

    @api.depends("line_ids", "line_ids.total", "line_ids.category_id.code")
    def _compute_contribucion_lines(self):
        """Líneas de contribuciones patronales (categoría COMP), para la pestaña aparte del recibo."""
        for slip in self:
            slip.contribucion_line_ids = slip.line_ids.filtered(
                lambda l: (l.category_id.code or "").upper() == "COMP"
            )

    # ══════════════════════════════════════════════
    # RESOLUCIÓN DE CONTRATO / ESTRUCTURA / LOTE
    # ══════════════════════════════════════════════

    def _get_context_run(self):
        """Lote del recibo; durante la generación masiva el recibo todavía no existe y el
        lote llega por contexto (asistente ``hr.payslip.employees``).

        @return hr.payslip.run (puede ser vacío).
        """
        if len(self) == 1 and self.payslip_run_id:
            return self.payslip_run_id
        ctx = self.env.context
        if ctx.get("active_model") == "hr.payslip.run" and ctx.get("active_id"):
            return self.env["hr.payslip.run"].browse(ctx["active_id"])
        return self.env["hr.payslip.run"]

    @api.model
    def _get_struct_for(self, contract, run, struct=False):
        """Estructura a usar: la especializada si el lote es Vacaciones / SAC / Liquidación
        Final; si no, la indicada, la del contrato o la default por tipo de salario.

        Así un mismo lote de Vacaciones o SAC sirve para jornalizados y mensualizados: cada recibo toma
        la variante de su tipo de salario (p. ej. `SAC_JORNAL_ARG` o `SAC_MENSUAL_ARG`).

        @param contract Contrato (`hr.version`) del recibo.
        @param run Lote (`hr.payslip.run`, puede ser vacío).
        @param struct Estructura pedida explícitamente (la del lote o la elegida en el recibo).
        @return hr.payroll.structure (puede ser vacío si no hay ninguna configurada).
        """
        tipo = run.tipo_liquidacion if run else None
        wage_type = contract.wage_type or "monthly"
        Version = self.env["hr.version"]
        if tipo in SPECIALIZED_RUN_TYPES:
            specialized = Version._get_default_struct(wage_type, tipo_liquidacion=tipo, company=contract.company_id)
            if specialized:
                return specialized
        return struct or contract.struct_id or Version._get_default_struct(
            wage_type, tipo_liquidacion=tipo, company=contract.company_id)

    @api.model_create_multi
    def create(self, vals_list):
        """Crea recibos completando contrato y estructura, y les agrega todas las entradas.

        Sin contrato, toma el primero vigente en el período; la estructura se resuelve con
        `_get_struct_for()`. Después de crear, `_ensure_input_lines()` agrega las entradas que falten
        (recibos creados por importación, XML o código).

        @param vals_list Lista de diccionarios de valores.
        @return Recibos creados.
        """
        for vals in vals_list:
            if not vals.get("employee_id"):
                continue
            run = self.env["hr.payslip.run"].browse(vals.get("payslip_run_id"))
            if not vals.get("contract_id") and vals.get("date_from") and vals.get("date_to"):
                employee = self.env["hr.employee"].browse(vals["employee_id"])
                contracts = employee._get_contracts(
                    date_start=fields.Date.to_date(vals["date_from"]),
                    date_end=fields.Date.to_date(vals["date_to"]),
                ).get(employee.id)
                if contracts:
                    vals["contract_id"] = contracts[0].id
            contract = self.env["hr.version"].browse(vals.get("contract_id"))
            if contract:
                struct = self.env["hr.payroll.structure"].browse(vals.get("struct_id"))
                struct = self._get_struct_for(contract, run, struct)
                if struct:
                    vals["struct_id"] = struct.id
        slips = super().create(vals_list)
        slips._ensure_input_lines()
        return slips

    def write(self, vals):
        """Al cambiar la estructura, agrega las entradas de la estructura nueva que falten.

        @param vals Valores a escribir.
        @return True.
        """
        res = super().write(vals)
        if "struct_id" in vals:
            self._ensure_input_lines()
        return res

    # ══════════════════════════════════════════════
    # NOVEDADES: CARGA AUTOMÁTICA EN LAS LÍNEAS DE ENTRADA
    # ══════════════════════════════════════════════

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        """Una línea por código de entrada de la estructura, con el valor automático ya cargado.

        Precedencia: valor del lote (``hr.payslip.run.novelty``) > valor del período
        (``_get_period_input_amounts``) > 0. La llama el módulo `payroll` al cambiar empleado o
        estructura en el formulario.

        @param contracts Contratos vigentes del empleado (se usa el primero).
        @param date_from Inicio del período.
        @param date_to Fin del período.
        @return Lista de diccionarios de `hr.payslip.input`.
        """
        if not contracts:
            return []
        contract = contracts[0]
        run = self._get_context_run()
        struct = (self.struct_id if len(self) == 1 else False) or run.struct_id
        struct = self._get_struct_for(contract, run, struct)
        return self._prepare_input_lines(contract, struct, date_from, date_to, run)

    @api.model
    def _prepare_input_lines(self, contract, struct, date_from, date_to, run, skip_codes=()):
        """Valores de las líneas de entrada de la estructura (una por código), con el valor
        automático cargado. ``skip_codes``: códigos que ya existen en el recibo.

        @param contract Contrato del recibo.
        @param struct Estructura salarial (se incluyen las reglas de las estructuras padre).
        @param date_from Inicio del período.
        @param date_to Fin del período.
        @param run Lote (puede ser vacío).
        @param skip_codes Códigos a omitir porque el recibo ya los tiene.
        @return Lista de diccionarios de `hr.payslip.input` (sin `payslip_id`).
        """
        rule_inputs = struct.get_structure_with_parents().get_all_rules().input_ids
        amounts = self._get_period_input_amounts(contract, date_from, date_to, run)
        amounts.update(run._get_novelty_amounts())

        res = []
        seen = set(skip_codes)
        for sequence, rule_input in enumerate(rule_inputs, start=1):
            if rule_input.code in seen:
                continue
            seen.add(rule_input.code)
            res.append({
                "name": rule_input.name,
                "code": rule_input.code,
                "contract_id": contract.id,
                "sequence": sequence,
                "amount": amounts.get(rule_input.code, 0.0),
            })
        return res

    def _ensure_input_lines(self):
        """Agrega, con su valor automático, las entradas de la estructura que le falten al
        recibo (recibos creados por importación, datos XML o código). No toca las existentes.

        Sólo recibos editables (borrador / en espera) con contrato y estructura. Garantiza que la matriz
        de novedades del lote tenga una celda por empleado y código.
        """
        vals_list = []
        for slip in self.filtered(lambda s: s.contract_id and s.struct_id and s.state in ("draft", "verify")):
            struct_codes = set(slip.struct_id.get_structure_with_parents().get_all_rules().input_ids.mapped("code"))
            if struct_codes <= set(slip.input_line_ids.mapped("code")):
                continue
            for vals in slip._prepare_input_lines(
                slip.contract_id, slip.struct_id, slip.date_from, slip.date_to, slip.payslip_run_id,
                skip_codes=slip.input_line_ids.mapped("code"),
            ):
                vals_list.append({**vals, "payslip_id": slip.id})
        if vals_list:
            self.env["hr.payslip.input"].create(vals_list)

    @api.model
    def _get_period_input_amounts(self, contract, date_from, date_to, run):
        """Valores automáticos de las novedades que se derivan del período, el calendario,
        las licencias aprobadas y la ficha del empleado. Punto de extensión (asistencias).

        Reglas de negocio:
        - `DED_SIRADIG`: deducción mensual estimada del F.572 (ficha del empleado), en todos los lotes.
        - Lote SAC: nada más (el SAC no lleva horas ni vacaciones).
        - `VAC_DIAS`: días corridos de vacaciones aprobadas dentro del período (Art. 151 LCT).
        - `APORTE_ADIC_SS`: monto fijo de la ficha, sólo en 2° Quincena y Mensual (una vez por mes).
        - Jornalizados (salvo lote de Vacaciones): `HS_NORM` = horas del calendario − vacaciones, y
          `FERIADO` = feriados en días laborables × horas por día (Art. 166 LCT: el feriado se paga).

        `payroll_arg_attendance` lo extiende para tomar `HS_NORM` y extras de las fichadas.

        @param contract Contrato del recibo.
        @param date_from Inicio del período.
        @param date_to Fin del período.
        @param run Lote (puede ser vacío).
        @return dict {código de entrada: importe}

        @bug C1 (docs/revision.md): `VAC_DIAS` se carga también en quincenas y mensuales aunque esas
             vacaciones ya se hayan pagado en un lote de Vacaciones: se pagan dos veces.
        @bug C13: resta días **corridos** × horas promedio (incluye sábados y domingos); una semana de
             vacaciones descuenta 61,6 hs en lugar de 44.
        @bug C14: el feriado vale `hours_per_day` (8,8 promedio) y no las horas de ese día del calendario
             (9 hs un lunes, como en el recibo de referencia).
        """
        employee = contract.employee_id
        tipo = run.tipo_liquidacion if run else None
        vals = {"DED_SIRADIG": employee.ganancias_otras_deducciones_mensual or 0.0}
        if tipo == "SAC":
            return vals

        vac_days = self._get_vacation_days(employee, date_from, date_to)
        vals["VAC_DIAS"] = vac_days
        if tipo in ("2° Quincena", "Mensual"):
            vals["APORTE_ADIC_SS"] = employee.aporte_adicional_ss_monto or 0.0

        cal = contract.resource_calendar_id
        if contract.wage_type == "hourly" and cal and tipo != "Vacaciones":
            hours_per_day = cal.hours_per_day or 8.0
            cal_hours = self._get_calendar_hours_for_period(cal, date_from, date_to)
            vals["HS_NORM"] = max(0.0, round(cal_hours - vac_days * hours_per_day, 2))
            holidays = self._get_calendar_public_holidays_count(cal, employee, date_from, date_to)
            vals["FERIADO"] = round(holidays * hours_per_day, 2)
        return vals

    def _set_input_amounts(self, amounts):
        """Escribe importes en las líneas de entrada por código, creando las que falten.

        Una línea nueva sólo se crea si el importe no es 0. Los códigos que no existen en la estructura
        igual se crean (con el nombre del `hr.rule.input` si existe), aunque ninguna regla los lea.

        @param amounts dict {código: importe}.
        """
        rule_inputs = self.env["hr.rule.input"]
        for slip in self:
            by_code = {line.code: line for line in slip.input_line_ids}
            to_create = []
            for code, amount in amounts.items():
                line = by_code.get(code)
                if line:
                    if line.amount != amount:
                        line.amount = amount
                elif amount:
                    name = rule_inputs.search([("code", "=", code)], limit=1).name or code
                    to_create.append({
                        "payslip_id": slip.id,
                        "contract_id": slip.contract_id.id,
                        "code": code,
                        "name": name,
                        "amount": amount,
                    })
            if to_create:
                self.env["hr.payslip.input"].create(to_create)

    def action_reload_period_inputs(self):
        """Vuelve a leer calendario, licencias, asistencias y ficha, y pisa las entradas automáticas.

        Los códigos con valor fijado en el lote no se tocan.

        Botón *Recargar Novedades del Período* (recibo y lote). Pisa también lo que el usuario haya
        corregido a mano en esos códigos (`HS_NORM`, `FERIADO`, `VAC_DIAS`, `DED_SIRADIG`, …).

        @return True.
        """
        self._ensure_input_lines()
        for slip in self.filtered(lambda s: s.state in ("draft", "verify") and s.contract_id):
            run = slip.payslip_run_id
            amounts = slip._get_period_input_amounts(slip.contract_id, slip.date_from, slip.date_to, run)
            for code in run._get_novelty_amounts():
                amounts.pop(code, None)
            slip._set_input_amounts(amounts)
        return True

    # ══════════════════════════════════════════════
    # FUENTES DE DATOS DEL PERÍODO
    # ══════════════════════════════════════════════

    @api.model
    def _get_calendar_hours_for_period(self, calendar, date_from, date_to):
        """Horas teóricas del período según el calendario de trabajo.

        Horas semanales = suma de las franjas del calendario (sin almuerzo; si hay franjas duplicadas
        para el mismo día y turno, se toma la mayor). Un período de hasta 16 días es una quincena y vale
        **dos semanas** (44 hs × 2 = 88 hs, convención de los recibos de referencia); uno más largo, las horas
        semanales × días / 7.

        @param calendar Calendario (`resource.calendar`) del contrato.
        @param date_from Inicio del período.
        @param date_to Fin del período.
        @return Horas (float, 1 decimal).

        @bug C15 (docs/revision.md): la quincena vale siempre 88 hs, tenga 10, 11 o 12 días hábiles.
        """
        if not calendar or not date_from or not date_to:
            return 0.0

        total_days = (date_to - date_from).days + 1

        # Agrupar por (día, turno) para inmunizar contra registros duplicados
        daily_hours = {}
        for s in calendar.attendance_ids.filtered(lambda a: a.day_period != "lunch"):
            key = (s.dayofweek, s.day_period)
            dur = s.hour_to - s.hour_from
            if key not in daily_hours or dur > daily_hours[key]:
                daily_hours[key] = dur

        if daily_hours:
            weekly_hours = round(sum(daily_hours.values()), 2)
        else:
            weekly_hours = calendar.hours_per_week or 44.0

        if weekly_hours <= 0:
            return 0.0

        # Quincenas (≤16 días): dos semanas. Ej: 44 hs/sem × 2 = 88 hs quincenales
        if total_days <= 16:
            return round(weekly_hours * 2.0, 1)
        return round(weekly_hours * (total_days / 7.0), 1)

    @api.model
    def _get_vacation_days(self, employee, date_from, date_to):
        """Días de vacaciones aprobadas (hr.leave) dentro del período.

        Detecta vacaciones por el tipo ``payroll_arg.holiday_status_vacaciones_lct``,
        por código VAC / VACACIONES o por nombre conteniendo 'vacac' / 'vacat'.
        Cuenta días **corridos** (Art. 151 LCT), recortando cada licencia a las fechas del período.

        @param employee Empleado.
        @param date_from Inicio del período.
        @param date_to Fin del período.
        @return Días (float).
        """
        if not employee or not date_from or not date_to:
            return 0.0

        dt_from = fields.Datetime.to_datetime(date_from)
        dt_to = fields.Datetime.to_datetime(date_to).replace(hour=23, minute=59, second=59)
        leaves = self.env["hr.leave"].search([
            ("employee_id", "=", employee.id),
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

        total_days = 0.0
        for leave in vacation_leaves:
            start = max(leave.date_from.date(), date_from)
            end = min(leave.date_to.date(), date_to)
            if end >= start:
                total_days += (end - start).days + 1
        return float(total_days)

    @api.model
    def _get_calendar_public_holidays_count(self, cal, employee, date_from, date_to):
        """Cantidad de feriados (hojas globales del calendario) en días laborables del período.

        Feriados = ausencias globales (`resource.calendar.leaves` sin recurso) del calendario o de
        todos los calendarios. Sólo cuentan los días de semana en que el calendario tiene horario: el
        feriado que cae en un día no laborable no se paga aparte (Art. 166 LCT).

        @param cal Calendario del contrato.
        @param employee Empleado (para su zona horaria si el calendario no tiene).
        @param date_from Inicio del período.
        @param date_to Fin del período.
        @return Cantidad de días (float).

        @bug C24 (docs/revision.md): usa la zona horaria del calendario y los calendarios del módulo no
             la fijan; un feriado guardado en hora argentina en un calendario en UTC cuenta dos días.
        """
        if not cal or not date_from or not date_to:
            return 0.0
        tz = pytz.timezone(cal.tz or employee.tz or DEFAULT_TZ)
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
        working_days = set(cal.attendance_ids.mapped("dayofweek"))
        holiday_days = set()
        for leaf in leaves:
            curr = max(date_from, pytz.utc.localize(leaf.date_from).astimezone(tz).date())
            end_d = min(date_to, pytz.utc.localize(leaf.date_to).astimezone(tz).date())
            while curr <= end_d:
                if str(curr.weekday()) in working_days:
                    holiday_days.add(curr)
                curr += relativedelta(days=1)
        return float(len(holiday_days))

    def _get_prev_month_gross(self):
        """Base de contribuciones de jornalizados quincenales: bruto remunerativo del último
        mes con recibos calculados anterior al período (todas las liquidaciones de ese mes:
        quincenas, SAC, vacaciones, ajustes). Se puede fijar a mano con prev_month_gross_manual.

        Replica el cuadro "Costo Total Empleado" de los recibos de referencia, que muestra las contribuciones
        del último mes declarado en el F.931 (las de la quincena todavía no se conocen). Cuentan los
        recibos en espera o hechos; si un mes no tiene recibos (licencia larga) se sigue hacia atrás.

        @return Importe en pesos (0 si no hay recibos anteriores).

        @bug C8 (docs/revision.md): sólo suma el remunerativo; la Obra Social y el sindicato también
             contribuyen sobre las sumas no remunerativas de convenio.
        """
        self.ensure_one()
        if self.prev_month_gross_manual > 0:
            return round(self.prev_month_gross_manual, 2)
        if not self.employee_id or not self.date_from:
            return 0.0
        domain = [
            ("employee_id", "=", self.employee_id.id),
            ("id", "!=", self._origin.id or 0),
            ("state", "in", ("done", "verify")),
        ]
        month_start = self.date_from.replace(day=1)
        last = self.search(domain + [("date_to", "<", month_start)], order="date_to desc", limit=1)
        if not last:
            return 0.0
        first_day = last.date_to.replace(day=1)
        last_day = first_day.replace(day=calendar.monthrange(first_day.year, first_day.month)[1])
        slips = self.search(domain + [("date_from", ">=", first_day), ("date_to", "<=", last_day)])
        return round(sum(slips.mapped("total_remunerativo")), 2)

    def _get_tope_imponible(self):
        """Tope imponible (base máxima, Art. 9 Ley 24.241) de los aportes del trabajador en este recibo.

        El del recibo si se cargó; si no, el de la compañía, **la mitad** en las quincenas (decisión
        confirmada: cada quincena se topea por separado con medio tope).

        @return Importe en pesos (0 = sin tope).

        @bug C9 (docs/revision.md): un lote de SAC usa el tope mensual completo; para el SAC la base
             máxima se calcula aparte (a verificar: 50% del tope del mes).
        """
        self.ensure_one()
        if self.tope_imponible_retenciones:
            return self.tope_imponible_retenciones
        tope = self.company_id.tope_imponible_max_retencion or 0.0
        return round(tope / 2.0, 2) if self.tipo_liquidacion in QUINCENA_TYPES else tope

    def _get_contrib_coefs(self):
        """(coef. Seg. Social, coef. Obra Social) del lote o, sin lote, de la compañía.

        Multiplican las contribuciones patronales (`result_qty` de las reglas COMP_*): 1 = alícuota
        plena; los recibos de referencia usan 0,10 y 0,15.

        @return Tupla (coef_ss, coef_os).
        """
        self.ensure_one()
        src = self.payslip_run_id or self.company_id
        return src.coef_contrib_ss, src.coef_contrib_os

    # ══════════════════════════════════════════════
    # CONTEXTO DE EVALUACIÓN DE REGLAS
    # ══════════════════════════════════════════════

    def _get_baselocaldict(self, contracts):
        """Agrega `inp(código)` al contexto de las reglas salariales: devuelve el importe de la entrada
        del recibo con ese código (0 si no existe). Es la única forma en que las reglas leen novedades.

        @param contracts Contratos del recibo.
        @return dict del contexto de evaluación.
        """
        localdict = super()._get_baselocaldict(contracts)
        amounts = {line.code: line.amount for line in self.input_line_ids if line.code}

        def inp(code):
            """Importe de la entrada `code` del recibo.

            @param code Código de la entrada (p. ej. 'HS_NORM').
            @return Importe, 0.0 si el recibo no tiene esa entrada.
            """
            return amounts.get(code, 0.0)

        localdict["inp"] = inp
        return localdict

    def get_payroll_dict(self, contracts):
        """Parámetros disponibles en las reglas como ``payroll.clave`` (p. ej. ``payroll.tope``).

        - `coef_ss`, `coef_os`: coeficientes de contribuciones (`_get_contrib_coefs()`).
        - `detraccion_sipa`: detracción mensual Ley 27.541 (compañía).
        - `tope`: tope imponible de este recibo (`_get_tope_imponible()`).
        - `prev_gross`: base de contribuciones del mes anterior (sólo quincenas, si no 0).
        - `is_q1`, `is_q2`: tipo de quincena (p. ej. el seguro de vida UOM no va en la 1°).

        @param contracts Contratos del recibo.
        @return dict de parámetros.
        """
        res = super().get_payroll_dict(contracts)
        coef_ss, coef_os = self._get_contrib_coefs()
        res.update({
            "coef_ss": coef_ss,
            "coef_os": coef_os,
            "detraccion_sipa": self.company_id.detraccion_sipa,
            "tope": self._get_tope_imponible(),
            # Sólo las quincenas toman la base del último mes; SAC / vacaciones / final
            # contribuyen sobre su propio remunerativo.
            "prev_gross": self._get_prev_month_gross() if self.tipo_liquidacion in QUINCENA_TYPES else 0.0,
            "is_q1": self.tipo_liquidacion == "1° Quincena",
            "is_q2": self.tipo_liquidacion == "2° Quincena",
        })
        return res

    def _calculate_ganancias_from_rules(self, cur_gross, cur_mandatory_ret):
        """Calcula Ganancias acumulativo desde la regla salarial RET_GANANCIAS.

        Método acumulativo de la RG 4003 (4ta categoría):

        1. Ganancia bruta acumulada del año = brutos de los meses anteriores (acumuladores) + el de este
           recibo.
        2. Menos aportes de ley acumulados (categoría DED calculada hasta la regla) y deducciones
           generales del SIRADIG (`DED_SIRADIG`).
        3. Menos deducciones personales del Art. 30 LIG (ganancia no imponible, especial, cónyuge,
           hijos) **proporcionales al mes**: anual × mes / 12.
        4. Impuesto acumulado con la escala del Art. 94 también proporcional al mes
           (`hr.ganancias.scale.calculate_annual_bracket()`).
        5. Retención del mes = impuesto acumulado − retenciones de los meses anteriores (nunca negativa).

        Guarda el resultado en el acumulador del empleado para ese año y mes (lo crea o lo pisa).
        Con *Override Retención Ganancias* devuelve el importe manual sin calcular ni guardar nada.

        @param cur_gross Bruto del recibo (hoy `categories.REM`).
        @param cur_mandatory_ret Aportes de ley del recibo (hoy `categories.DED`, negativo).
        @return Retención del mes en pesos (positiva).

        @bug C2 (docs/revision.md): el acumulador es uno por mes y se **pisa**: la 2° quincena (o un
             SAC / vacaciones del mismo mes) borra el bruto y la retención de la 1°, no la resta y los meses
             siguientes acumulan de menos.
        @bug C3: el bruto no incluye las sumas no remunerativas (gravadas).
        @bug C4: el seguro de vida UOM y el aporte adicional se calculan después y no se deducen.
        @bug C6: ignora pluriempleo, pagos a cuenta, topes de deducciones y devoluciones.
        @bug T2: escribe el acumulador aunque el recibo quede en borrador o se borre.
        """
        self.ensure_one()
        if self.ganancias_override > 0:
            return round(self.ganancias_override, 2)

        target_date = self.date_to or fields.Date.today()
        year = target_date.year
        month = target_date.month

        scale = self.env["hr.ganancias.scale"].get_scale_for_date(target_date, self.company_id)
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
        siradig_input = self.input_line_ids.filtered(lambda i: i.code == "DED_SIRADIG")[:1]
        cur_other_ded = siradig_input.amount

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
            "retention_applied": retention_this_month,
            "payslip_id": self.id,
        }
        if acc:
            acc.write(vals)
        else:
            acc_model.create(vals)

        return retention_this_month

    # ══════════════════════════════════════════════
    # ONCHANGES
    # ══════════════════════════════════════════════

    @api.onchange("employee_id", "date_from", "date_to")
    def onchange_employee(self):
        """Formulario del recibo: fechas del lote y estructura según el contrato y el tipo de lote.

        Completa las fechas vacías con las del lote y, si el contrato pide otra estructura (p. ej. lote
        de SAC), la cambia y recarga las entradas.

        @return Resultado del onchange de `payroll`.
        """
        for slip in self:
            run = slip.payslip_run_id
            if run:
                slip.date_from = slip.date_from or run.date_start
                slip.date_to = slip.date_to or run.date_end
        res = super().onchange_employee()
        for slip in self.filtered(lambda s: s.contract_id and s.state in (False, "draft")):
            struct = slip._get_struct_for(slip.contract_id, slip.payslip_run_id, slip.struct_id)
            if struct != slip.struct_id:
                slip.struct_id = struct
                slip.onchange_struct_id()
        return res

    # ══════════════════════════════════════════════
    # COMPUTE LEAVES / WORKED DAYS
    # ══════════════════════════════════════════════

    def _compute_leave_days(self, contract, day_from, day_to):
        """Líneas de ausencias de *Días trabajados* con códigos argentinos.

        Las ausencias sin código (o GLOBAL) se clasifican por nombre: vacaciones → `VAC`, enfermedad →
        `ENF`, el resto → `LEAVE`. Horas y días en positivo. Informativo: las reglas no leen estas
        líneas, leen las entradas.

        @param contract Contrato.
        @param day_from Inicio del período.
        @param day_to Fin del período.
        @return Lista de diccionarios de `hr.payslip.worked_days`.
        """
        res = super()._compute_leave_days(contract, day_from, day_to)
        fixed_res = []
        for line in res:
            line_dict = dict(line)
            name = (line_dict.get("name") or "").lower()
            code = line_dict.get("code")
            if not code or code == "GLOBAL":
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
        """Línea de días/horas trabajados descontando vacaciones, licencias y enfermedad. Informativo
        (las reglas leen las entradas, no estas líneas).

        @param contract Contrato.
        @param day_from Inicio del período.
        @param day_to Fin del período.
        @return Diccionario de la línea de días trabajados.
        """
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
    # COMPUTE SHEET
    # ══════════════════════════════════════════════

    def compute_sheet(self):
        """Valida y calcula. No modifica las líneas de entrada.

        Antes de calcular completa contrato y estructura si faltan, y frena con un mensaje claro si el
        recibo no tiene contrato vigente, estructura o sueldo/valor hora.

        @return Resultado de `compute_sheet` de `payroll`.
        @throws UserError Sin contrato vigente, sin estructura o con básico en 0.
        """
        for slip in self:
            if not slip.contract_id:
                slip.contract_id = slip._get_employee_contracts()[:1]
            if not slip.contract_id:
                raise UserError(
                    f"El recibo de '{slip.employee_id.name}' no tiene contrato vigente en el período "
                    f"{slip.date_from} – {slip.date_to}."
                )
            if not slip.struct_id:
                slip.struct_id = slip._get_struct_for(slip.contract_id, slip.payslip_run_id)
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
        return super().compute_sheet()

    # ══════════════════════════════════════════════
    # AFIP F931
    # ══════════════════════════════════════════════

    def _line_qty(self, *codes):
        """Suma de las cantidades de las líneas con esos códigos (horas o días liquidados).

        @param codes Códigos de regla.
        @return Cantidad total.
        """
        return sum(self.line_ids.filtered(lambda l: l.code in codes).mapped("quantity"))

    def _get_afip_info_f931(self):
        """Datos del trabajador para el F.931 (SICOSS) y el registro 4 del Libro de Sueldos Digital.

        Tres bloques: `fijos` (CUIL, cónyuge, hijos, condición, actividad, obra social, zona, modalidad,
        convencionado…), `variables` (situación de revista) e `importes` (bases y conceptos agrupados:
        sueldo, horas extras, SAC, vacaciones; días u horas trabajadas).

        @return dict con las claves `fijos`, `variables` e `importes`.

        @bug E1 (docs/revision.md): las bases Remuneración 1 a 10 son todas el remunerativo del recibo
             (sin tope, sin no remunerativo para Obra Social, sin detracción); jornalizados con
             `k_dias` = 0; valores de relleno (CUIL 20000000000, actividad 049, zona 18…) si faltan datos.
        """
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
            if line.code in F931_VACACIONES_CODES:
                vacaciones_val += line.total
            elif line.code in F931_HS_EXTRAS_CODES:
                hs_extras_val += line.total
                hs_extras_cant += int(line.quantity or 0)
            elif line.code in F931_SAC_CODES:
                sac_val += line.total
            elif line.salary_rule_id.tipo_concepto == "1":
                sueldo_val += line.total

        total_rem = self.total_remunerativo
        total_norem = self.total_no_remunerativo

        if contract.wage_type == "hourly":
            k_dias = 0.0
            k_horas = int(self._line_qty("BASIC_HORAS", "HS_EXT_50", "HS_EXT_100"))
        else:
            k_dias = float(self._line_qty("BASIC_MENSUAL") or DIAS_BASE_MENSUAL_LCT)
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
        """Conceptos del recibo para el registro 3 del Libro de Sueldos Digital.

        Una fila por línea con importe (sin totalizadores ni contribuciones), con el código de concepto
        del empleador (`afip_code` de la regla, o el código de la regla), la cantidad, la unidad y el
        importe (negativo en las retenciones: el generador lo informa como débito).

        @return Lista de dict {concepto, cantidad, importe, unidades}.

        @bug E2 (docs/revision.md): varias reglas tienen `afip_code` "0" o comparten código (FERIADO y
             HS_EXT_50 → 130000), y la antigüedad informa cantidad 1 con unidad "%".
        """
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
    # RECIBO DICT
    # ══════════════════════════════════════════════

    def _to_recibo_dict(self, nro_liq=1, tipo_liq="Mensual"):
        """Datos del recibo de sueldo (Art. 140 LCT) en el formato de `py_arg_reports` (recibo PDF).

        Incluye empresa y último depósito de Seguridad Social (Art. 140 inc. j), empleado, conceptos
        (cantidad, base e importe por línea), totales y el pie de "Composición salarial": aportes desde
        las líneas calculadas y contribuciones recalculadas sobre el bruto del recibo, con el 15% de Obra
        Social para el Fondo Solidario (ANSSAL) agrupado en Seguridad Social como en el F.931.

        @param nro_liq Número de liquidación del mes.
        @param tipo_liq Tipo de liquidación que se imprime.
        @return dict del recibo.

        @bug E4 (docs/revision.md): completa con datos inventados lo que falta (CUIT 20123456780,
             número de calle "100", fecha de ingreso 2020-01-01, categoría "Operario"…), y manda el
             nombre completo como `first_name`.
        @bug C8: el pie calcula la contribución de Obra Social sobre remunerativo + no remunerativo,
             pero la línea `COMP_OS` usa sólo el remunerativo.
        """
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
                    # Valor unitario / base imponible de la línea (valor hora, base topeada, monto fijo)
                    "base": round(abs(line.amount), 2),
                    "importe": round(abs(line.total), 2),
                }
            )
            orden += 1

        rem = self.total_remunerativo
        no_rem = self.total_no_remunerativo
        ret = self.total_retenciones
        neto = self.neto_liquidacion

        lines_by_code = {line.code: line for line in self.line_ids}

        def line_total(code):
            """Importe (positivo) de la línea con ese código.

            @param code Código de regla.
            @return Importe, 0.0 si el recibo no tiene esa línea.
            """
            line = lines_by_code.get(code)
            return abs(line.total) if line else 0.0

        # ── Detalle de la Composición Salarial (Pie de página según normativa AFIP F.931) ──
        # Aportes: desde las líneas calculadas. Contribuciones: sobre el bruto del mes actual
        # (las líneas COMP_* usan la base del último mes declarado). El 15% de Obra Social
        # (ANSSAL / FSR) se agrupa dentro de Seguridad Social como en el F.931.
        coef_ss, _coef_os = self._get_contrib_coefs()

        pie_ap_sin = line_total("RET_SIND")
        pie_ct_sin = 0.0

        pie_ap_inssjp = line_total("RET_INSSJP")
        pie_ct_inssjp = round(rem * company.inssjp_patronal_rate / 100.0 * coef_ss, 2)

        pie_art = round(rem * company.art_variable_rate / 100.0, 2)
        pie_svida = line_total("COMP_SCVO")

        base_os = round(rem + no_rem, 2)
        tot_ap_os = line_total("RET_OS")
        pie_ap_os = round(tot_ap_os * (1 - ANSSAL_SHARE), 2)
        anssal_ap = round(tot_ap_os * ANSSAL_SHARE, 2)
        os_pat_rate = company.os_patronal_rate / 100.0
        pie_ct_os = round(base_os * os_pat_rate * (1 - ANSSAL_SHARE), 2)
        anssal_ct = round(base_os * os_pat_rate * ANSSAL_SHARE, 2)
        anssal_total = round(anssal_ct + anssal_ap, 2)

        is_q2 = self.tipo_liquidacion == "2° Quincena"
        jub = lines_by_code.get("RET_JUB")
        if is_q2 and jub:
            # Q2: aporte sin redondear para calzar con el borrador del F.931
            pie_ap_ss = round(abs(jub.amount) * jub.rate / 100.0 + anssal_ap, 2)
        else:
            pie_ap_ss = round(line_total("RET_JUB") + anssal_ap, 2)

        ct_jub_ind = round(rem * company.jubilacion_patronal_rate / 100.0 * coef_ss, 2)
        ct_aaff_ind = round(rem * company.aaff_patronal_rate / 100.0 * coef_ss, 2)
        ct_fne_ind = round(rem * company.fne_patronal_rate / 100.0 * coef_ss, 2)
        pie_ct_ss_base = round(ct_jub_ind + ct_aaff_ind + ct_fne_ind, 2)
        pie_ct_ss = round(pie_ct_ss_base + (anssal_total if is_q2 else anssal_ap), 2)

        total_contrib = self.total_contribuciones
        costo_total = self.costo_total_empleador

        periodo_str = self.date_from.strftime("%Y-%m") if self.date_from else datetime.today().strftime("%Y-%m")
        fecha_pago_str = str(self.payment_date or self.date_to or datetime.today().date())

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
                "basico": contract.wage if contract else 0.0,
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
        """Genera y descarga el Recibo de Sueldo oficial en PDF para esta liquidación individual.

        Si el recibo no está calculado lo calcula. Usa el diseño 4 (con contribuciones patronales) de
        `py_arg_reports` y deja el PDF adjunto al recibo.

        @return Acción de descarga del adjunto.
        @throws UserError Si la librería no pudo generar el PDF.
        """
        self.ensure_one()
        if not self.line_ids:
            self.compute_sheet()

        temp_dir = tempfile.mkdtemp()
        try:
            periodo_tag = self.date_from.strftime("%Y%m") if self.date_from else "202601"
            emp_clean = (self.employee_id.name or f"empleado_{self.employee_id.id}").replace(" ", "_")
            filename = f"Recibo_{emp_clean}_{periodo_tag}"

            recibo_payload = [self._to_recibo_dict(
                nro_liq=self.payslip_run_id.afip_nro_liquidacion or 1,
                tipo_liq=self.payslip_run_id.tipo_liquidacion or "Mensual",
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

            attachment = self.env["ir.attachment"].create({
                "name": f"{filename}.pdf",
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
        """Abre el asistente de exportación de reportes para este recibo individual.

        @return Acción de ventana del asistente `payroll.arg.export.wizard`.
        """
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
                "default_payslip_run_id": self.payslip_run_id.id,
            },
        }

    def action_open_payslip(self):
        """Abre la vista formulario del recibo individual (botón de la lista de recibos del lote).

        @return Acción de ventana del recibo.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "res_id": self.id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "current",
        }


class HrPayslipWorkedDays(models.Model):
    """Líneas de días trabajados con código obligatorio: si no viene, se deduce del nombre."""

    _inherit = "hr.payslip.worked_days"

    code = fields.Char(
        string="Código",
        required=True,
        default="WORK100",
        help="Código de identificación del concepto de días u horas trabajadas/ausencias.",
    )

    @staticmethod
    def _guess_code(name):
        """Código de una línea de días trabajados según su nombre: vacaciones → VAC, enfermedad → ENF,
        trabajo normal → WORK100, el resto → LEAVE.

        @param name Nombre de la línea.
        @return Código.
        """
        n = (name or "").lower()
        if any(k in n for k in ("vacac", "vacat")):
            return "VAC"
        if any(k in n for k in ("enferm", "sick")):
            return "ENF"
        if "work" in n or "normal" in n:
            return "WORK100"
        return "LEAVE"

    @api.onchange("name")
    def _onchange_name(self):
        """Propone el código al escribir el nombre de la línea."""
        if not self.code and self.name:
            self.code = self._guess_code(self.name)

    @api.model_create_multi
    def create(self, vals_list):
        """Completa el código faltante a partir del nombre.

        @param vals_list Lista de diccionarios de valores.
        @return Líneas creadas.
        """
        for vals in vals_list:
            if not vals.get("code"):
                vals["code"] = self._guess_code(vals.get("name"))
        return super().create(vals_list)

    def write(self, vals):
        """No permite dejar el código vacío: lo deduce del nombre.

        @param vals Valores a escribir.
        @return True.
        """
        if "code" in vals and not vals["code"]:
            vals["code"] = self._guess_code(vals.get("name") or self[:1].name)
        return super().write(vals)


class HrPayslipLine(models.Model):
    """Línea de recibo con 4 decimales en el importe unitario."""

    _inherit = "hr.payslip.line"

    # 4 decimales en el importe unitario: 30 × (sueldo / 30) debe dar el sueldo exacto
    amount = fields.Float(digits=(16, 4))
