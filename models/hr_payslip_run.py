import calendar
from datetime import datetime
from odoo import fields, models, api
from odoo.exceptions import UserError

from .hr_contract import DIAS_BASE_MENSUAL_LCT


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    tipo_liquidacion = fields.Selection(
        [
            ("1° Quincena", "1° Quincena"),
            ("2° Quincena", "2° Quincena"),
            ("Quincenal", "Quincenal"),
            ("Mensual", "Mensual"),
            ("Vacaciones", "Vacaciones"),
            ("SAC", "SAC (Aguinaldo)"),
            ("Liquidación Final", "Liquidación Final"),
            ("Ajustes", "Ajustes"),
        ],
        string="Tipo de Liquidación AFIP",
        default="Mensual",
        required=True,
        help="Tipo de liquidación informado a la AFIP / ARCA en el Libro de Sueldos Digital",
    )
    has_hourly_payslips = fields.Boolean(
        string="Tiene Jornalizados",
        compute="_compute_has_hourly_payslips",
        store=True,
        help="Indica si el lote contiene al menos un recibo de empleado jornalizado.",
    )
    is_quincenal = fields.Boolean(
        string="Es Liquidación Quincenal",
        compute="_compute_is_quincenal",
        store=True,
        help="Indica si el tipo de liquidación es quincenal (1° Quincena, 2° Quincena, Quincenal).",
    )
    afip_nro_liquidacion = fields.Integer(
        string="N° de Liquidación en el Mes",
        default=1,
        required=True,
        help="Número correlativo de la liquidación en el período mensual (ej: 1 para 1° Quincena, 2 para 2° Quincena)",
    )
    payment_date = fields.Date(
        string="Fecha de Pago",
        default=fields.Date.today,
        required=True,
        help="Fecha efectiva de pago a consignar en el recibo de sueldo y AFIP",
    )
    slip_ids = fields.One2many(
        "hr.payslip",
        "payslip_run_id",
        string="Payslips",
        readonly=False,
    )

    # ──────────────────────────────────────────────
    # Novedades Variables de la Quincena
    # ──────────────────────────────────────────────
    monto_premio_produccion = fields.Float(
        string="Monto Premio Producción ($)",
        default=0.0,
        help="Monto fijo de Premio Producción para esta quincena. "
             "Se aplica a los empleados marcados con el toggle 'Premio Prod.' en la tabla de recibos.",
    )
    monto_presentismo = fields.Float(
        string="Monto Presentismo ($)",
        default=0.0,
        help="Monto fijo de Presentismo para esta quincena. "
             "Se aplica a los empleados marcados con el toggle 'Presentismo' en la tabla de recibos.",
    )
    monto_portitulo = fields.Float(
        string="Monto Portítulo ($)",
        default=0.0,
        help="Monto fijo de Portítulo para esta quincena. "
             "Se aplica a los empleados marcados con el toggle 'Portítulo' en la tabla de recibos.",
    )
    cant_feriados = fields.Float(
        string="Feriados (Hs)",
        default=0.0,
        help="Cantidad de horas de feriado en la quincena para el lote. "
             "Se propaga por defecto a los recibos que no tengan override manual.",
    )
    monto_gratif_no_rem = fields.Float(
        string="Monto Gratif. Extraord. NR ($)",
        default=0.0,
        help="Monto de la Gratificación Extraordinaria No Remunerativa para esta quincena. "
             "Se aplica a los recibos de la 2da quincena con el concepto activo.",
    )
    monto_compens_no_rem = fields.Float(
        string="Monto Compens. Extraord. NR ($)",
        default=0.0,
        help="Monto de la Compensación Extraordinaria No Remunerativa para esta quincena. "
             "Se aplica a los recibos de la 2da quincena con el concepto activo.",
    )
    precio_vianda = fields.Float(
        string="Precio Vianda ($)",
        default=0.0,
        digits=(16, 2),
        help="Precio unitario de cada vianda en esta quincena. Se utiliza para calcular el descuento de viandas.",
    )
    coef_contrib_ss = fields.Float(
        string="Coef. Contrib. Seg. Social",
        default=lambda self: self.env.company.coef_contrib_ss,
        digits=(16, 4),
        help="Coeficiente sobre Jubilación, Ley 19.032, AAFF y FNE patronales. "
             "Se toma de la compañía y se propaga a los recibos del lote.",
    )
    coef_contrib_os = fields.Float(
        string="Coef. Contrib. Obra Social",
        default=lambda self: self.env.company.coef_contrib_os,
        digits=(16, 4),
        help="Coeficiente sobre la contribución patronal de Obra Social. "
             "Se toma de la compañía y se propaga a los recibos del lote.",
    )

    def action_open_export_wizard(self):
        self.ensure_one()
        return {
            "name": "Exportar Reportes de Nómina Argentina",
            "type": "ir.actions.act_window",
            "res_model": "payroll.arg.export.wizard",
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "new",
            "context": {"default_payslip_run_id": self.id},
        }

    @api.depends("slip_ids", "slip_ids.contract_id", "tipo_liquidacion")
    def _compute_has_hourly_payslips(self):
        hourly_types = ("1° Quincena", "2° Quincena", "Quincenal")
        for run in self:
            is_quincenal = run.tipo_liquidacion in hourly_types
            has_hourly_slip = any(
                slip.contract_id.wage_type == "hourly"
                for slip in run.slip_ids
                if slip.contract_id
            )
            if run.tipo_liquidacion == "Mensual":
                run.has_hourly_payslips = False
            elif is_quincenal:
                run.has_hourly_payslips = True
            else:
                run.has_hourly_payslips = has_hourly_slip

    @api.depends("tipo_liquidacion")
    def _compute_is_quincenal(self):
        hourly_types = ("1° Quincena", "2° Quincena", "Quincenal")
        for run in self:
            run.is_quincenal = bool(
                run.tipo_liquidacion and (
                    run.tipo_liquidacion in hourly_types or "Quincena" in run.tipo_liquidacion
                )
            )

    @api.onchange("tipo_liquidacion")
    def _onchange_tipo_liquidacion(self):
        """Sugiere la estructura salarial según el tipo de liquidación.
        Las fechas del período NO se tocan: las define el usuario."""
        if self.tipo_liquidacion == "1° Quincena":
            self.afip_nro_liquidacion = 1
            self.struct_id = self.env["hr.version"]._get_default_struct("hourly", tipo_liquidacion=self.tipo_liquidacion)
        elif self.tipo_liquidacion == "2° Quincena":
            self.afip_nro_liquidacion = 2
            self.struct_id = self.env["hr.version"]._get_default_struct("hourly", tipo_liquidacion=self.tipo_liquidacion)
        elif self.tipo_liquidacion == "Quincenal":
            self.struct_id = self.env["hr.version"]._get_default_struct("hourly", tipo_liquidacion=self.tipo_liquidacion)
        elif self.tipo_liquidacion == "Mensual":
            self.afip_nro_liquidacion = 1
            self.struct_id = self.env["hr.version"]._get_default_struct("monthly", tipo_liquidacion=self.tipo_liquidacion)
        elif self.tipo_liquidacion in ("Vacaciones", "SAC", "Liquidación Final"):
            if self.slip_ids:
                all_hourly = all(s.contract_id.wage_type == "hourly" for s in self.slip_ids if s.contract_id)
                all_monthly = all(s.contract_id.wage_type == "monthly" for s in self.slip_ids if s.contract_id)
                if all_hourly:
                    self.struct_id = self.env["hr.version"]._get_default_struct("hourly", tipo_liquidacion=self.tipo_liquidacion)
                elif all_monthly:
                    self.struct_id = self.env["hr.version"]._get_default_struct("monthly", tipo_liquidacion=self.tipo_liquidacion)
                else:
                    self.struct_id = False
            else:
                self.struct_id = False

        if self.date_end:
            self.payment_date = self.date_end

    @api.onchange("date_end")
    def _onchange_date_end(self):
        if self.date_end:
            self.payment_date = self.date_end

    def action_open_hours_wizard(self):
        self.ensure_one()
        if not self.slip_ids:
            raise UserError(
                "El lote no tiene recibos generados todavía.\n\n"
                "1. Primero presione 'Generar Recibos' para seleccionar los empleados.\n"
                "2. Luego ingrese a 'Carga Masiva de Horas' para cargar las novedades de la quincena."
            )
        hourly_slips = self.slip_ids.filtered(
            lambda s: s.contract_id and s.contract_id.wage_type == "hourly"
        )
        if not hourly_slips:
            raise UserError(
                "El lote no contiene recibos de operarios jornalizados (con contrato por hora).\n\n"
                "Verifique que los empleados seleccionados tengan contratos con tipo de salario 'Por hora'."
            )
        return {
            "name": "Carga Masiva de Horas - Jornales Quincenales",
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip.run.hours.wizard",
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "new",
            "context": {"default_payslip_run_id": self.id},
        }

    def action_apply_run_variables(self):
        """Aplica novedades y recalcula automáticamente los recibos del lote."""
        return self.action_compute_payslips()

    def action_sync_attendance_hours(self):
        """Sincroniza masivamente las asistencias reales de todos los recibos del lote."""
        self.ensure_one()
        slips = self.slip_ids.filtered(lambda s: s.state in ("draft", "verify"))
        if not slips:
            raise UserError("No hay recibos pendientes de confirmación en este lote.")
        count = 0
        for slip in slips:
            if hasattr(slip, "action_sync_attendance_hours"):
                slip.action_sync_attendance_hours()
            slip.compute_sheet()
            count += 1
        self.invalidate_recordset(["slip_ids"])
        return True

    @api.onchange("date_start", "date_end")
    def _onchange_dates(self):
        """Propaga automáticamente el cambio de período a los recibos y valida que fecha inicio <= fecha fin."""
        warning = None
        if self.date_start and self.date_end:
            if self.date_start > self.date_end:
                warning = {
                    "title": "Inconsistencia de Fechas",
                    "message": "La fecha de inicio no puede ser posterior a la fecha de fin.",
                }
            if self.slip_ids:
                for slip in self.slip_ids.filtered(lambda s: s.state in ("draft", "verify")):
                    slip.date_from = self.date_start
                    slip.date_to = self.date_end

        if warning:
            return {"warning": warning}

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ("date_start", "date_end", "cant_feriados", "monto_gratif_no_rem", "monto_compens_no_rem", "coef_contrib_ss", "coef_contrib_os", "precio_vianda")):
            for run in self:
                slips_to_update = run.slip_ids.filtered(lambda s: s.state in ("draft", "verify"))
                slip_vals = {}
                if "date_start" in vals:
                    slip_vals["date_from"] = vals["date_start"]
                if "date_end" in vals:
                    slip_vals["date_to"] = vals["date_end"]
                if slip_vals and slips_to_update:
                    slips_to_update.write(slip_vals)
                    for slip in slips_to_update:
                        slip._sync_liquidation_summary()

                if "cant_feriados" in vals:
                    fer_slips = slips_to_update.filtered(lambda s: not s.feriados_manual)
                    if fer_slips:
                        fer_slips.write({"cant_feriados": vals["cant_feriados"]})

                if "monto_gratif_no_rem" in vals:
                    gratif_slips = slips_to_update.filtered(lambda s: not s.gratif_no_rem_manual)
                    if gratif_slips:
                        gratif_slips.write({"monto_gratif_no_rem": vals["monto_gratif_no_rem"]})

                if "monto_compens_no_rem" in vals:
                    comp_slips = slips_to_update.filtered(lambda s: not s.compens_no_rem_manual)
                    if comp_slips:
                        comp_slips.write({"monto_compens_no_rem": vals["monto_compens_no_rem"]})

                if "precio_vianda" in vals:
                    slips_to_update.write({"precio_vianda": vals["precio_vianda"]})

                if "coef_contrib_ss" in vals:
                    slips_to_update.write({"coef_contrib_ss": vals["coef_contrib_ss"]})

                if "coef_contrib_os" in vals:
                    slips_to_update.write({"coef_contrib_os": vals["coef_contrib_os"]})
        return res

    def action_confirm_payslips(self):
        """Confirma todos los recibos del lote en estado borrador o en espera."""
        self.ensure_one()
        slips = self.slip_ids.filtered(lambda s: s.state in ("draft", "verify"))
        if not slips:
            raise UserError("No hay recibos pendientes de confirmación en este lote.")
        for slip in slips:
            slip.action_payslip_done()
        return True

    def close_payslip_run(self):
        """Al cerrar el lote, confirma los recibos pendientes y pasa el lote a 'close'."""
        for run in self:
            slips_to_confirm = run.slip_ids.filtered(lambda s: s.state in ("draft", "verify"))
            if slips_to_confirm:
                for slip in slips_to_confirm:
                    slip.action_payslip_done()
        return super().close_payslip_run()

    def action_compute_payslips(self):
        self.ensure_one()
        slips = self.slip_ids.filtered(lambda s: s.state in ("draft", "verify"))
        if not slips:
            raise UserError("No hay recibos pendientes de confirmación en este lote.")
        for slip in slips:
            slip.compute_sheet()
        self.invalidate_recordset(["slip_ids"])
        return True

    def _prepare_lsd_payload(self):
        self.ensure_one()
        slips = self.slip_ids.filtered(lambda s: s.state in ["verify", "done"])
        if not slips:
            raise UserError("No hay recibos calculados o en estado Verificado/Hecho en este lote.")

        # F7.3: Validación pre-export
        self._validate_slips_for_export(slips)

        company = self.company_id
        cuit = (company.cuit or company.vat or "20123456780").replace("-", "").strip()
        periodo_date = self.date_start or fields.Date.today()
        is_quincena = "Quincena" in self.tipo_liquidacion or self.tipo_liquidacion == "Quincenal"
        ds_base = 15 if is_quincena else DIAS_BASE_MENSUAL_LCT

        empleados_data = []
        for slip in slips:
            empleados_data.append(
                {
                    "empleado_id": slip.employee_id.id,
                    "empleado_legajo": slip.employee_id.legajo or slip.employee_id.id,
                    "dias_tope": 15 if is_quincena else 30,
                    "info_f931": slip._get_afip_info_f931(),
                    "conceptos_liquidados": slip._get_conceptos_liquidados_lsd(),
                }
            )

        payload = {
            "periodo": str(periodo_date),
            "empresa": company.name,
            "cuit": cuit,
            "cantidad_liquidaciones": 1,
            "liquidaciones": [
                {
                    "id": self.id,
                    "nro_liq": self.afip_nro_liquidacion,
                    "tipo_liquidacion": self.tipo_liquidacion,
                    "fecha_pago": str(self.payment_date or fields.Date.today()),
                    "dias_base": ds_base,
                    "empleados_liquidados": empleados_data,
                }
            ],
        }
        return payload

    def _validate_slips_for_export(self, slips):
        """Valida que todos los recibos tengan datos requeridos antes de exportar (F7.3)."""
        errors = []
        for slip in slips:
            emp_name = slip.employee_id.name or f"ID:{slip.employee_id.id}"
            if not slip.employee_id.cuil:
                errors.append(f"{emp_name}: falta CUIL")
            if not slip.contract_id:
                errors.append(f"{emp_name}: falta contrato activo")
            if not slip.neto_liquidacion and slip.neto_liquidacion != 0:
                errors.append(f"{emp_name}: neto no calculado — ¿se computó el recibo?")
        if errors:
            raise UserError(
                "Datos incompletos para exportar. Corrija antes de continuar:\n\n"
                + "\n".join(errors[:20])
            )

    def _prepare_recibos_payload(self):
        self.ensure_one()
        slips = self.slip_ids.filtered(lambda s: s.state in ["verify", "done"])
        if not slips:
            raise UserError("No hay recibos calculados en este lote para generar.")

        return [
            slip._to_recibo_dict(
                nro_liq=self.afip_nro_liquidacion,
                tipo_liq=self.tipo_liquidacion,
            )
            for slip in slips
        ]

    def _prepare_f931_payload(self):
        self.ensure_one()
        slips = self.slip_ids.filtered(lambda s: s.state in ["verify", "done"])
        if not slips:
            raise UserError("No hay recibos calculados para exportar F.931.")

        cuit = (self.company_id.cuit or self.company_id.vat or "20123456780").replace("-", "").strip()
        periodo_str = self.date_start.strftime("%Y%m") if self.date_start else datetime.today().strftime("%Y%m")

        empleados_f931 = []
        for slip in slips:
            info = slip._get_afip_info_f931()
            row = {}
            row.update(info["fijos"])
            row.update(info["variables"])
            row.update(info["importes"])
            empleados_f931.append(row)

        return {
            "cuit": cuit,
            "periodo": periodo_str,
            "txt_empleados": empleados_f931,
        }
