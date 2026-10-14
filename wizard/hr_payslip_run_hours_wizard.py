import base64
import csv
import io
from odoo import api, fields, models
from odoo.exceptions import UserError


class HrPayslipRunHoursWizard(models.TransientModel):
    _name = "hr.payslip.run.hours.wizard"
    _description = "Carga Masiva de Horas para Jornales"

    payslip_run_id = fields.Many2one("hr.payslip.run", string="Lote de Recibos", required=True)
    line_ids = fields.One2many(
        "hr.payslip.run.hours.line",
        "wizard_id",
        string="Horas por Empleado",
    )
    global_hs_norm = fields.Float(
        string="Horas Normales para Todos",
        default=88.0,
        help="Horas normales estándar a aplicar a todos los empleados del lote con un solo clic.",
    )
    csv_file = fields.Binary(string="Archivo CSV")
    csv_filename = fields.Char(string="Nombre Archivo")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        run_id = self.env.context.get("active_id") or self.env.context.get("default_payslip_run_id")
        if run_id:
            run = self.env["hr.payslip.run"].browse(run_id)
            res["payslip_run_id"] = run.id
            lines = []
            # F8.2: Solo incluir recibos de jornalizados
            hourly_slips = run.slip_ids.filtered(
                lambda s: s.contract_id and s.contract_id.wage_type == "hourly"
            )
            for slip in hourly_slips:
                input_dict = {inp.code: inp.amount for inp in slip.input_line_ids}
                cal = slip.contract_id.resource_calendar_id if slip.contract_id else False
                cal_hours = slip.hours_theoretical or (
                    slip._get_calendar_hours_for_period(cal, slip.date_from, slip.date_to) if cal else 0.0
                )
                hs_norm = input_dict.get("HS_NORM", slip.hours_normal or cal_hours or 88.0)
                hs_ext50 = input_dict.get("HS_EXT50", slip.hours_ext50 or 0.0)
                hs_ext100 = input_dict.get("HS_EXT100", slip.hours_ext100 or 0.0)
                vac_dias = input_dict.get("VAC_DIAS", slip.total_days_vacation or 0.0)
                wage = slip.contract_id.wage if slip.contract_id else (
                    getattr(slip.employee_id, "wage", 0.0)
                )
                lines.append((0, 0, {
                    "payslip_id": slip.id,
                    "employee_id": slip.employee_id.id,
                    "legajo": slip.employee_id.legajo,
                    "hourly_wage": wage or 0.0,
                    "hours_theoretical": cal_hours or 0.0,
                    "hs_norm": hs_norm or 0.0,
                    "hs_ext50": hs_ext50,
                    "hs_ext100": hs_ext100,
                    "vac_dias": vac_dias,
                }))
            res["line_ids"] = lines
            if lines:
                # Sugerir la moda o el primer valor teórico
                first_theor = lines[0][2].get("hours_theoretical", 88.0)
                res["global_hs_norm"] = first_theor if first_theor > 0 else 88.0
        return res

    def action_apply_global_hours(self):
        """Aplica el valor de global_hs_norm a todos los operarios de la tabla."""
        self.ensure_one()
        if self.global_hs_norm <= 0:
            raise UserError("Ingrese un valor de horas mayor a 0.")
        for line in self.line_ids:
            line.hs_norm = self.global_hs_norm
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "new",
        }

    def action_populate_from_calendars(self):
        """Rellena las horas normales según el horario de 2 semanas de cada contrato."""
        self.ensure_one()
        for line in self.line_ids:
            line.hs_norm = line.hours_theoretical if line.hours_theoretical > 0 else 88.0
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Horas según Calendario",
                "message": "Se completaron las horas teóricas basadas en el horario de 44 hs semanales (88 hs quincenales).",
                "type": "info",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "res_id": self.id,
                    "view_mode": "form",
                    "views": [[False, "form"]],
                    "target": "new",
                },
            },
        }

    def action_populate_from_attendance(self):
        """Lee las fichadas reales de hr.attendance para cada empleado en el período y carga hs_norm."""
        self.ensure_one()
        import pytz
        from datetime import datetime, time

        run = self.payslip_run_id
        start_date = run.date_start
        end_date = run.date_end

        if "hr.attendance" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Módulo de Asistencias",
                    "message": "El modelo de asistencias (hr.attendance) no se encuentra disponible en la base de datos.",
                    "type": "warning",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window",
                        "res_model": self._name,
                        "res_id": self.id,
                        "view_mode": "form",
                        "views": [[False, "form"]],
                        "target": "new",
                    },
                },
            }

        attendance_obj = self.env["hr.attendance"]
        loaded_count = 0
        ot_count = 0
        for line in self.line_ids:
            slip = line.payslip_id or self.payslip_run_id.slip_ids.filtered(lambda s: s.employee_id == line.employee_id)[:1]
            contract = slip.contract_id if slip else False
            if not contract and hasattr(line.employee_id, "contract_id"):
                contract = line.employee_id.contract_id
            if not contract and hasattr(line.employee_id, "version_id"):
                contract = line.employee_id.version_id
            calendar = contract.resource_calendar_id if contract else False
            tz = pytz.timezone(calendar.tz or line.employee_id.tz or "America/Argentina/Cordoba") if calendar else pytz.utc
            tz_start = tz.localize(datetime.combine(start_date, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
            tz_end = tz.localize(datetime.combine(end_date, time.max)).astimezone(pytz.utc).replace(tzinfo=None)

            attendances = attendance_obj.search([
                ("employee_id", "=", line.employee_id.id),
                ("check_in", ">=", tz_start),
                ("check_in", "<=", tz_end),
                ("check_out", "!=", False),
            ])
            if attendances:
                breakdown = self.env["hr.payslip"]._compute_attendance_hours_breakdown(
                    attendances, calendar=calendar, employee=line.employee_id
                )
                tot = breakdown["hours_normal"] + breakdown["hours_ext50"] + breakdown["hours_ext100"]
                if tot > 0.1:
                    line.hs_norm = breakdown["hours_normal"]
                    line.hs_ext50 = breakdown["hours_ext50"]
                    line.hs_ext100 = breakdown["hours_ext100"]
                    loaded_count += 1
                    if (breakdown["hours_ext50"] + breakdown["hours_ext100"]) > 0:
                        ot_count += 1

        if loaded_count > 0:
            msg = (
                f"Se cargaron fichadas reales para {loaded_count} empleado(s). "
                f"Se detectaron horas extras para {ot_count} empleado(s) (50% y 100% según jornada legal)."
            )
        else:
            msg = "No se encontraron fichadas reales con horas trabajadas en el período para los empleados."

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Horas desde Asistencias",
                "message": msg,
                "type": "success" if loaded_count > 0 else "warning",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": self._name,
                    "res_id": self.id,
                    "view_mode": "form",
                    "views": [[False, "form"]],
                    "target": "new",
                },
            },
        }

    def action_apply_and_recompute(self):
        self.ensure_one()
        for line in self.line_ids:
            slip = line.payslip_id or self.payslip_run_id.slip_ids.filtered(lambda s: s.employee_id == line.employee_id)[:1]
            if not slip:
                continue
            contract = slip.contract_id
            if not contract and hasattr(slip.employee_id, "version_id"):
                contract = slip.employee_id.version_id
            if not contract:
                continue

            slip.hours_normal = line.hs_norm
            slip.hours_ext50 = line.hs_ext50
            slip.hours_ext100 = line.hs_ext100
            slip.total_days_vacation = line.vac_dias

            inputs_to_set = {
                "HS_NORM": ("Horas Normales Trabajadas", line.hs_norm),
                "HS_EXT50": ("Horas Extras al 50%", line.hs_ext50),
                "HS_EXT100": ("Horas Extras al 100%", line.hs_ext100),
                "VAC_DIAS": ("Días de Vacaciones Gozadas", line.vac_dias),
            }

            for code, (name, amount) in inputs_to_set.items():
                existing = slip.input_line_ids.filtered(lambda i: i.code == code)
                if amount > 0:
                    if existing:
                        existing[0].write({"amount": amount})
                        if len(existing) > 1:
                            existing[1:].unlink()
                    else:
                        self.env["hr.payslip.input"].create({
                            "payslip_id": slip.id,
                            "contract_id": contract.id,
                            "code": code,
                            "name": name,
                            "amount": amount,
                        })
                else:
                    if existing:
                        existing.unlink()

            slip.compute_sheet()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Carga Masiva Exitosa",
                "message": f"Se actualizaron y recalcularon {len(self.line_ids)} recibos correctamente.",
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_import_csv(self):
        self.ensure_one()
        if not self.csv_file:
            raise UserError("Seleccione un archivo CSV para importar.")

        try:
            content = base64.b64decode(self.csv_file).decode("utf-8-sig")
        except Exception:
            try:
                content = base64.b64decode(self.csv_file).decode("latin1")
            except Exception as e:
                raise UserError(f"Error al decodificar archivo CSV: {e}")

        # Check delimiter
        delimiter = ";" if ";" in content.splitlines()[0] else ","
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)

        lines_by_legajo = {l.legajo: l for l in self.line_ids if l.legajo}
        lines_by_name = {l.employee_id.name.lower().strip(): l for l in self.line_ids if l.employee_id}
        lines_by_cuil = {l.employee_id.cuil.strip(): l for l in self.line_ids if l.employee_id and l.employee_id.cuil}

        matched = 0
        for row in reader:
            legajo_val = row.get("legajo") or row.get("Legajo") or row.get("LEGAJO")
            name_val = row.get("nombre") or row.get("Nombre") or row.get("NOMBRE")
            cuil_val = (row.get("cuil") or row.get("CUIL") or "").replace("-", "").strip()

            line = None
            if legajo_val:
                try:
                    line = lines_by_legajo.get(int(str(legajo_val).strip()))
                except ValueError:
                    pass
            if not line and cuil_val:
                line = lines_by_cuil.get(cuil_val)
            if not line and name_val:
                line = lines_by_name.get(name_val.lower().strip())

            if line:
                matched += 1
                for key in ["hs_norm", "HS_NORM", "horas_normales", "Horas Normales"]:
                    if key in row and row[key] != "":
                        line.hs_norm = float(str(row[key]).replace(",", "."))
                        break
                for key in ["hs_ext50", "HS_EXT50", "horas_extras_50", "Horas Extras 50"]:
                    if key in row and row[key] != "":
                        line.hs_ext50 = float(str(row[key]).replace(",", "."))
                        break
                for key in ["hs_ext100", "HS_EXT100", "horas_extras_100", "Horas Extras 100"]:
                    if key in row and row[key] != "":
                        line.hs_ext100 = float(str(row[key]).replace(",", "."))
                        break
                for key in ["vac_dias", "VAC_DIAS", "dias_vacaciones", "Vacaciones"]:
                    if key in row and row[key] != "":
                        line.vac_dias = float(str(row[key]).replace(",", "."))
                        break

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Importación CSV Completada",
                "message": f"Se procesaron {matched} empleados desde el CSV. Revise la grilla y presione 'Guardar y Recalcular'.",
                "sticky": False,
                "type": "info",
            },
        }


class HrPayslipRunHoursLine(models.TransientModel):
    _name = "hr.payslip.run.hours.line"
    _description = "Línea de Horas por Empleado"

    wizard_id = fields.Many2one("hr.payslip.run.hours.wizard", required=True, ondelete="cascade")
    payslip_id = fields.Many2one("hr.payslip", string="Recibo", required=False)
    employee_id = fields.Many2one("hr.employee", string="Empleado", required=False)
    legajo = fields.Integer(string="Legajo", readonly=True)
    hourly_wage = fields.Float(string="Valor Hora ($)", readonly=True)
    hours_theoretical = fields.Float(string="Hs Calendario", readonly=True, help="Horas teóricas esperadas según el calendario de trabajo.")
    hs_norm = fields.Float(string="Hs Normales (Override)", default=0.0, help="Horas normales trabajadas. Al guardar, se aplica el override en el recibo.")
    hs_ext50 = fields.Float(string="Hs Extras 50% (Override)", default=0.0, help="Horas extras al 50%. Al guardar, se aplica el override en el recibo.")
    hs_ext100 = fields.Float(string="Hs Extras 100% (Override)", default=0.0, help="Horas extras al 100%. Al guardar, se aplica el override en el recibo.")
    vac_dias = fields.Float(string="Días Vacaciones", default=0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("employee_id") and vals.get("payslip_id"):
                slip = self.env["hr.payslip"].browse(vals["payslip_id"])
                if slip and slip.employee_id:
                    vals["employee_id"] = slip.employee_id.id
            if not vals.get("payslip_id") and vals.get("employee_id") and vals.get("wizard_id"):
                wiz = self.env["hr.payslip.run.hours.wizard"].browse(vals["wizard_id"])
                if wiz.payslip_run_id:
                    slip = wiz.payslip_run_id.slip_ids.filtered(lambda s: s.employee_id.id == vals["employee_id"])[:1]
                    if slip:
                        vals["payslip_id"] = slip.id
        return super().create(vals_list)
