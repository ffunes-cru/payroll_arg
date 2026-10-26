"""@file
Lote de liquidación argentino (`hr.payslip.run`): tipo de liquidación ARCA, novedades del lote (valores
fijos y matriz por empleado), acciones masivas y armado de los datos del Libro de Sueldos Digital, el
F.931 y los recibos PDF.
"""
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

from .hr_contract import DIAS_BASE_MENSUAL_LCT

## Estados de recibo que todavía se pueden modificar y recalcular.
EDITABLE_SLIP_STATES = ("draft", "verify")
## Novedades en horas / días / unidades (primera matriz del lote); el resto son importes en pesos.
QUANTITY_INPUT_CODES = (
    "HS_NORM", "HS_EXT50", "HS_EXT100", "FERIADO", "VAC_DIAS", "CANT_VIANDAS", "SAC_DIAS", "VAC_NO_GOZ",
)


class HrPayslipRun(models.Model):
    """Lote de liquidación: una quincena, un mes, unas vacaciones, un SAC o una liquidación final.

    El tipo de liquidación decide la estructura de cada recibo (`hr.payslip._get_struct_for()`), qué
    novedades se cargan solas, el tope imponible y la base de contribuciones.
    """

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
    novelty_ids = fields.One2many(
        "hr.payslip.run.novelty",
        "run_id",
        string="Valores del Lote",
        help="Novedades con el mismo valor para todo el lote. Se cargan al generar los recibos "
             "o con el botón Aplicar de cada línea.",
    )
    input_qty_line_ids = fields.One2many(
        "hr.payslip.input",
        "payslip_run_id",
        string="Horas, Días y Cantidades",
        domain=[("code", "in", QUANTITY_INPUT_CODES)],
    )
    input_amount_line_ids = fields.One2many(
        "hr.payslip.input",
        "payslip_run_id",
        string="Importes ($)",
        domain=[("code", "not in", QUANTITY_INPUT_CODES)],
    )
    coef_contrib_ss = fields.Float(
        string="Coef. Contrib. Seg. Social",
        default=lambda self: self.env.company.coef_contrib_ss,
        digits=(16, 4),
        help="Coeficiente sobre Jubilación, Ley 19.032, AAFF y FNE patronales de los recibos del lote.",
    )
    coef_contrib_os = fields.Float(
        string="Coef. Contrib. Obra Social",
        default=lambda self: self.env.company.coef_contrib_os,
        digits=(16, 4),
        help="Coeficiente sobre la contribución patronal de Obra Social de los recibos del lote.",
    )

    def _get_novelty_amounts(self):
        """{código: valor} de las novedades fijadas en el lote.

        @return dict {código: valor}.
        """
        return {n.code: n.amount for n in self.novelty_ids if n.code}

    def _get_editable_slips(self):
        """Recibos del lote en borrador o en espera.

        @return hr.payslip.
        @throws UserError Si no hay ninguno.
        """
        slips = self.slip_ids.filtered(lambda s: s.state in EDITABLE_SLIP_STATES)
        if not slips:
            raise UserError("No hay recibos en borrador o en espera en este lote.")
        return slips

    # ══════════════════════════════════════════════
    # ONCHANGES / CRUD
    # ══════════════════════════════════════════════

    @api.onchange("tipo_liquidacion")
    def _onchange_tipo_liquidacion(self):
        """Sugiere estructura y N° de liquidación según el tipo. Las fechas las define el usuario.

        1° Quincena / Mensual → liquidación 1; 2° Quincena → 2. Quincenas → estructura de jornales;
        Mensual → de mensuales; Vacaciones / SAC / Final → sin estructura (la resuelve cada recibo).
        """
        Version = self.env["hr.version"]
        tipo = self.tipo_liquidacion
        if tipo in ("1° Quincena", "Mensual"):
            self.afip_nro_liquidacion = 1
        elif tipo == "2° Quincena":
            self.afip_nro_liquidacion = 2

        if tipo in ("1° Quincena", "2° Quincena", "Quincenal"):
            self.struct_id = Version._get_default_struct("hourly", tipo_liquidacion=tipo)
        elif tipo == "Mensual":
            self.struct_id = Version._get_default_struct("monthly", tipo_liquidacion=tipo)
        else:
            # Vacaciones / SAC / Liquidación Final: cada recibo resuelve la estructura
            # especializada según el tipo de salario de su contrato.
            self.struct_id = False

        if self.date_end:
            self.payment_date = self.date_end

    @api.onchange("date_start", "date_end")
    def _onchange_dates(self):
        """La fecha de pago sigue al fin del período; avisa si las fechas están invertidas.

        @return Advertencia o None.
        """
        if self.date_end:
            self.payment_date = self.date_end
        if self.date_start and self.date_end and self.date_start > self.date_end:
            return {
                "warning": {
                    "title": "Inconsistencia de Fechas",
                    "message": "La fecha de inicio no puede ser posterior a la fecha de fin.",
                }
            }

    def write(self, vals):
        """Las fechas nuevas del lote se copian a sus recibos editables.

        @param vals Valores a escribir.
        @return True.

        @bug T3 (docs/revision.md): no recarga las novedades automáticas (horas, feriados, vacaciones)
             del período nuevo; hay que usar *Recargar Novedades del Período*.
        """
        res = super().write(vals)
        slip_vals = {}
        if "date_start" in vals:
            slip_vals["date_from"] = vals["date_start"]
        if "date_end" in vals:
            slip_vals["date_to"] = vals["date_end"]
        if slip_vals:
            self.slip_ids.filtered(lambda s: s.state in EDITABLE_SLIP_STATES).write(slip_vals)
        return res

    # ══════════════════════════════════════════════
    # ACCIONES
    # ══════════════════════════════════════════════

    def action_reload_period_inputs(self):
        """Relee calendario, licencias, asistencias y ficha del empleado en todos los recibos.

        @return True.
        """
        self.ensure_one()
        self._get_editable_slips().action_reload_period_inputs()
        return True

    def action_compute_payslips(self):
        """Recalcula todos los recibos editables del lote (botón *Recalcular Recibos*).

        @return True.
        """
        self.ensure_one()
        self._get_editable_slips().compute_sheet()
        return True

    def action_confirm_payslips(self):
        """Confirma todos los recibos del lote en estado borrador o en espera.

        @return True.
        """
        self.ensure_one()
        for slip in self._get_editable_slips():
            # action_payslip_done de OCA no es multi-registro (lee prevent_compute_on_confirm)
            slip.action_payslip_done()
        return True

    def close_payslip_run(self):
        """Al cerrar el lote, confirma los recibos pendientes y pasa el lote a 'close'.

        @return Resultado de `close_payslip_run` de `payroll`.
        """
        for slip in self.slip_ids.filtered(lambda s: s.state in EDITABLE_SLIP_STATES):
            slip.action_payslip_done()
        return super().close_payslip_run()

    def action_open_input_import(self):
        """Abre la importación de novedades desde CSV.

        @return Acción de ventana del asistente.
        """
        self.ensure_one()
        return {
            "name": "Importar Novedades (CSV)",
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip.run.input.import",
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "new",
            "context": {"default_payslip_run_id": self.id},
        }

    def action_open_export_wizard(self):
        """Abre el asistente de exportaciones (recibos PDF, LSD, F.931, bancos).

        @return Acción de ventana del asistente.
        """
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

    # ══════════════════════════════════════════════
    # EXPORTACIONES
    # ══════════════════════════════════════════════

    def _prepare_lsd_payload(self):
        """Datos del Libro de Sueldos Digital de este lote (una liquidación) para `py_arg_reports`.

        Toma los recibos en espera o hechos. Días base: 15 en quincenas, 30 en el resto.

        @return dict con período, CUIT y la liquidación con sus empleados (F.931 + conceptos).
        @throws UserError Sin recibos calculados o con datos faltantes (`_validate_slips_for_export()`).
        """
        self.ensure_one()
        slips = self.slip_ids.filtered(lambda s: s.state in ["verify", "done"])
        if not slips:
            raise UserError("No hay recibos calculados o en estado Verificado/Hecho en este lote.")

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

        return {
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

    def _validate_slips_for_export(self, slips):
        """Valida que todos los recibos tengan datos requeridos antes de exportar.

        Hoy exige CUIL, contrato y recibo calculado. Muestra hasta 20 errores juntos.

        @param slips Recibos a exportar.
        @throws UserError Si falta algún dato.
        """
        errors = []
        for slip in slips:
            emp_name = slip.employee_id.name or f"ID:{slip.employee_id.id}"
            if not slip.employee_id.cuil:
                errors.append(f"{emp_name}: falta CUIL")
            if not slip.contract_id:
                errors.append(f"{emp_name}: falta contrato activo")
            if not slip.line_ids:
                errors.append(f"{emp_name}: recibo sin calcular")
        if errors:
            raise UserError(
                "Datos incompletos para exportar. Corrija antes de continuar:\n\n"
                + "\n".join(errors[:20])
            )

    def _prepare_recibos_payload(self):
        """Datos de los recibos PDF del lote (recibos en espera o hechos).

        @return Lista de dict de `hr.payslip._to_recibo_dict()`.
        @throws UserError Sin recibos calculados.
        """
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
        """Datos del TXT del F.931 (SICOSS) con los recibos de este lote: una fila por recibo.

        @return dict con CUIT, período y filas.
        @throws UserError Sin recibos calculados.

        @bug E1 (docs/revision.md): el F.931 es mensual por CUIL, pero se arma por lote: con dos
             quincenas salen dos declaraciones, cada una con la mitad del mes. Tampoco valida CUIL.
        """
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
