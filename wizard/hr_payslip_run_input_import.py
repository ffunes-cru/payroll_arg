"""@file
Importación de novedades del lote desde un CSV (horas, premios, viandas…): una fila por empleado y una
columna por código de entrada.
"""
import base64
import csv
import io

from odoo import fields, models
from odoo.exceptions import UserError

## Encabezados históricos del asistente de horas → código de entrada.
HEADER_ALIASES = {
    "hs_norm": "HS_NORM",
    "horas_normales": "HS_NORM",
    "horas normales": "HS_NORM",
    "hs_ext50": "HS_EXT50",
    "horas_extras_50": "HS_EXT50",
    "horas extras 50": "HS_EXT50",
    "hs_ext100": "HS_EXT100",
    "horas_extras_100": "HS_EXT100",
    "horas extras 100": "HS_EXT100",
    "vac_dias": "VAC_DIAS",
    "dias_vacaciones": "VAC_DIAS",
    "vacaciones": "VAC_DIAS",
}
## Columnas que identifican al empleado (no son novedades).
KEY_HEADERS = ("legajo", "cuil", "nombre")


class HrPayslipRunInputImport(models.TransientModel):
    """Importa novedades por empleado desde un CSV.

    Una fila por empleado, identificado por ``legajo``, ``cuil`` o ``nombre``. Cada
    columna restante cuyo encabezado sea un código de entrada (``HS_NORM``,
    ``PRESENTISMO``, ``CANT_VIANDAS``...) se escribe en la línea de entrada del recibo.

    Ver el ejemplo data/ejemplo_carga_masiva_horas.csv y docs/operacion.md, sección "Importar novedades".
    """

    _name = "hr.payslip.run.input.import"
    _description = "Importar Novedades del Lote desde CSV"

    payslip_run_id = fields.Many2one("hr.payslip.run", string="Lote", required=True)
    csv_file = fields.Binary(string="Archivo CSV", required=True)
    csv_filename = fields.Char(string="Nombre Archivo")

    def _read_rows(self):
        """Lee el CSV (UTF-8 o Latin-1; separador `;` o `,` según la primera línea).

        @return Lista de dict {encabezado: valor}.
        @throws UserError Archivo vacío.
        """
        raw = base64.b64decode(self.csv_file)
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = raw.decode("latin1")
        lines = content.splitlines()
        if not lines:
            raise UserError("El archivo CSV está vacío.")
        delimiter = ";" if ";" in lines[0] else ","
        return list(csv.DictReader(io.StringIO(content), delimiter=delimiter))

    @staticmethod
    def _to_float(value):
        """Número de una celda, aceptando coma decimal.

        @param value Texto de la celda.
        @return float.
        @throws UserError Si no es un número.
        """
        try:
            return float(str(value).strip().replace(",", "."))
        except ValueError as e:
            raise UserError(f"Valor numérico inválido en el CSV: '{value}'") from e

    def action_import(self):
        """Escribe las novedades del CSV en los recibos editables del lote.

        Busca el recibo por legajo, CUIL o nombre (en ese orden). Las celdas vacías no se tocan.

        @return Notificación con los empleados cargados y los que no tienen recibo en el lote.

        @bug U1 (docs/revision.md): una columna con un código que no existe (p. ej. un error de tipeo)
             se guarda como entrada huérfana que ninguna regla lee, sin avisar.
        """
        self.ensure_one()
        slips = self.payslip_run_id._get_editable_slips()
        by_legajo = {str(s.employee_id.legajo): s for s in slips if s.employee_id.legajo}
        by_cuil = {s.employee_id.cuil: s for s in slips if s.employee_id.cuil}
        by_name = {(s.employee_id.name or "").strip().lower(): s for s in slips}

        matched, unmatched = 0, []
        for row in self._read_rows():
            row = {(k or "").strip(): v for k, v in row.items()}
            lowered = {k.lower(): v for k, v in row.items()}
            legajo = (lowered.get("legajo") or "").strip()
            cuil = (lowered.get("cuil") or "").replace("-", "").strip()
            name = (lowered.get("nombre") or "").strip().lower()
            slip = by_legajo.get(legajo) or by_cuil.get(cuil) or by_name.get(name)
            if not slip:
                unmatched.append(legajo or cuil or name or "?")
                continue

            amounts = {}
            for header, value in row.items():
                if header.lower() in KEY_HEADERS or value in (None, ""):
                    continue
                code = HEADER_ALIASES.get(header.lower(), header.upper())
                amounts[code] = self._to_float(value)
            slip._set_input_amounts(amounts)
            matched += 1

        message = f"Se cargaron novedades para {matched} empleado(s). Recalcule el lote."
        if unmatched:
            message += f" Sin recibo en el lote: {', '.join(unmatched[:10])}."
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Importación CSV",
                "message": message,
                "type": "warning" if unmatched else "success",
                "sticky": bool(unmatched),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
