import base64
import os
import tempfile
from pathlib import Path

from odoo import fields, models
from odoo.exceptions import UserError

from py_arg_reports.reporters.recibo_sueldo.base import ReciboDownloader
from py_arg_reports.reporters.libro_sueldo_digital.reporter import genera_txt_lsd
from py_arg_reports.reporters.f931.reporter import genera_txt_f931
from py_arg_reports.reporters.acreditaciones.galicia import AcreditacionGalicia
from py_arg_reports.reporters.acreditaciones.santander import AcreditacionSantander


class PayrollArgExportWizard(models.TransientModel):
    _name = "payroll.arg.export.wizard"
    _description = "Wizard de Exportación de Reportes de Nómina Argentina"

    payslip_run_id = fields.Many2one("hr.payslip.run", string="Lote de Liquidación", required=False)
    payslip_id = fields.Many2one("hr.payslip", string="Recibo de Sueldo", required=False)
    report_type = fields.Selection(
        [
            ("recibo_pdf", "Recibos de Sueldo (PDF)"),
            ("lsd_txt", "Libro de Sueldos Digital (AFIP LSD TXT)"),
            ("f931_txt", "Declaración Jurada F.931 (SICOSS TXT)"),
            ("banco_galicia", "Acreditación Bancaria (Galicia Excel)"),
            ("banco_santander", "Acreditación Bancaria (Santander TXT)"),
        ],
        string="Tipo de Reporte",
        default="recibo_pdf",
        required=True,
    )
    recibo_layout = fields.Selection(
        [
            ("1", "Layout 1 - Estándar"),
            ("2", "Layout 2 - Doble recibo (Original y Duplicado)"),
            ("3", "Layout 3 - Con gráfico de composición"),
            ("4", "Layout 4 - Con Contribuciones Patronales"),
        ],
        string="Diseño del Recibo",
        default="4",
    )
    state = fields.Selection(
        [("choose", "Elegir"), ("get", "Descargar")], default="choose"
    )
    file_data = fields.Binary(string="Archivo Generado", readonly=True)
    file_name = fields.Char(string="Nombre del Archivo", readonly=True)

    def action_generate_report(self):
        self.ensure_one()
        slip = self.payslip_id
        run = self.payslip_run_id or (slip.payslip_run_id if slip else False)
        if not run and not slip:
            raise UserError("Debe indicar un lote de liquidación o un recibo individual.")

        temp_dir = tempfile.mkdtemp()
        company = slip.company_id if slip else run.company_id
        cuit = (company.cuit or company.vat or "20123456780").replace("-", "").strip()
        periodo_date = (slip.date_from if slip else (run.date_start if run else fields.Date.today())) or fields.Date.today()
        periodo_tag = periodo_date.strftime("%Y%m")

        try:
            if self.report_type == "recibo_pdf":
                if slip:
                    emp_clean = (slip.employee_id.name or f"empleado_{slip.employee_id.id}").replace(" ", "_")
                    filename = f"Recibo_{emp_clean}_{periodo_tag}"
                    tipo_liq = getattr(run, "tipo_liquidacion", None)
                    if not tipo_liq:
                        tipo_liq = "Quincenal" if (slip.contract_id and slip.contract_id.wage_type == "hourly") else "Mensual"
                    recibos_payload = [slip._to_recibo_dict(
                        nro_liq=getattr(run, "afip_nro_liquidacion", 1) or 1,
                        tipo_liq=tipo_liq,
                    )]
                else:
                    recibos_payload = run._prepare_recibos_payload()
                    filename = f"Recibos_{run.name.replace(' ', '_')}_{periodo_tag}"

                downloader = ReciboDownloader(
                    json_data=recibos_payload,
                    output_path=temp_dir,
                    filename=filename,
                    base_version=int(self.recibo_layout or 4),
                )
                file_path, err = downloader.descargar_recibo()
                if not file_path or err:
                    raise UserError(f"Error generando recibos de sueldo: {err}")

                with open(file_path, "rb") as f:
                    file_content = f.read()
                out_name = f"{filename}.pdf"

            elif not run:
                raise UserError("Este tipo de reporte requiere procesar un lote completo de liquidación.")

            elif self.report_type == "lsd_txt":
                lsd_payload = run._prepare_lsd_payload()
                filename = f"LSD_{cuit}_{periodo_tag}_Liq{run.afip_nro_liquidacion}"
                ok, err = genera_txt_lsd(
                    json_data=lsd_payload,
                    output_path=temp_dir,
                    filename=filename,
                )
                if not ok or err:
                    raise UserError(f"Error generando Libro de Sueldos Digital: {err}")

                # py_arg_reports genera f"{filename}_{nro}.txt" o f"{filename}.txt"
                created_files = [f for f in os.listdir(temp_dir) if f.startswith(filename)]
                if not created_files:
                    raise UserError("No se encontró el archivo generado de Libro de Sueldos Digital.")

                target_file = os.path.join(temp_dir, created_files[0])
                with open(target_file, "rb") as f:
                    file_content = f.read()
                out_name = created_files[0]

            elif self.report_type == "f931_txt":
                f931_payload = run._prepare_f931_payload()
                filename = f"F931_{cuit}_{periodo_tag}"
                ok, err = genera_txt_f931(
                    json_data=f931_payload,
                    output_path=temp_dir,
                    filename=filename,
                )
                if not ok or err:
                    raise UserError(f"Error generando F.931: {err}")

                target_file = os.path.join(temp_dir, f"{filename}.txt")
                with open(target_file, "rb") as f:
                    file_content = f.read()
                out_name = f"{filename}.txt"

            elif self.report_type == "banco_galicia":
                empleados_galicia = []
                for slip in run.slip_ids.filtered(lambda s: s.state in ["verify", "done"]):
                    if slip.neto_liquidacion > 0:
                        empleados_galicia.append(
                            {
                                "nombre": slip.employee_id.name,
                                "apellido": "",
                                "nro_cuenta": slip.employee_id.cbu or "0000000000000000000000",
                                "importe_pago": slip.neto_liquidacion,
                            }
                        )
                galicia_data = {"empleados": empleados_galicia}
                out_name = f"Acreditacion_Galicia_{periodo_tag}.xlsx"
                target_file = os.path.join(temp_dir, out_name)
                banco = AcreditacionGalicia(galicia_data)
                ok, err = banco.generate_file(target_file)
                if not ok or err:
                    raise UserError(f"Error generando acreditaciones Galicia: {err}")

                with open(target_file, "rb") as f:
                    file_content = f.read()

            elif self.report_type == "banco_santander":
                empleados_santander = []
                for slip in run.slip_ids.filtered(lambda s: s.state in ["verify", "done"]):
                    if slip.neto_liquidacion > 0:
                        parts = (slip.employee_id.name or "").strip().split(" ", 1)
                        first_name = parts[0] if parts else "Empleado"
                        last_name = parts[1] if len(parts) > 1 else first_name
                        empleados_santander.append(
                            {
                                "nombre": first_name,
                                "apellido": last_name,
                                "cuil": slip.employee_id.cuil or "20000000000",
                                "legajo": str(slip.employee_id.legajo or slip.employee_id.id),
                                "direccion": slip.employee_id.workplace_location or "Córdoba",
                                "cbu": slip.employee_id.cbu or "0000000000000000000000",
                                "importe_pago": slip.neto_liquidacion,
                            }
                        )
                f_pago = run.payment_date or fields.Date.today()
                p_date = run.date_start or fields.Date.today()
                total_neto = sum(e["importe_pago"] for e in empleados_santander)
                santander_data = {
                    "empresa": {
                        "razon_social": run.company_id.name or "Empresa",
                        "cuit": cuit,
                    },
                    "liquidacion": {
                        "total_pago": total_neto,
                        "periodo_anio": str(p_date.year),
                        "periodo_mes": str(p_date.month).zfill(2),
                        "fecha_pago_anio": str(f_pago.year),
                        "fecha_pago_mes": str(f_pago.month).zfill(2),
                        "fecha_pago_dia": str(f_pago.day).zfill(2),
                    },
                    "empleados": empleados_santander,
                    "extras": {
                        "nro_de_acuerdo": "01",
                        "codigo_forma_pago": "50",
                    },
                }
                out_name = f"Acreditacion_Santander_{periodo_tag}.txt"
                target_file = os.path.join(temp_dir, out_name)
                banco = AcreditacionSantander(santander_data)
                ok, err = banco.generate_file(target_file)
                if not ok or err:
                    raise UserError(f"Error generando acreditaciones Santander: {err}")

                with open(target_file, "rb") as f:
                    file_content = f.read()

            self.write(
                {
                    "file_data": base64.b64encode(file_content),
                    "file_name": out_name,
                    "state": "get",
                }
            )

        finally:
            # Limpiar archivos temporales
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

        return {
            "type": "ir.actions.act_window",
            "res_model": "payroll.arg.export.wizard",
            "view_mode": "form",
            "views": [[False, "form"]],
            "res_id": self.id,
            "target": "new",
        }
