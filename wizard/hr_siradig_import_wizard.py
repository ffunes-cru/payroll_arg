"""@file
Importación del F.572 Web (SIRADIG) descargado de ARCA, en XML o en ZIP con varios empleados.
"""
import base64
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from odoo import api, fields, models
from odoo.exceptions import UserError


class HrSiradigImportWizard(models.TransientModel):
    """Asistente de importación de F.572: crea o actualiza la declaración y opcionalmente la aplica a la
    ficha del empleado."""

    _name = "hr.siradig.import.wizard"
    _description = "Asistente de Importación SIRADIG F.572 (AFIP / ARCA)"

    file_data = fields.Binary(
        string="Archivo F.572 (XML o ZIP de AFIP)",
        required=True,
        help="Archivo descargado del servicio 'SIRADIG - Empleador' de AFIP. Puede ser un archivo .ZIP (con múltiples F.572) o un .XML individual.",
    )
    file_name = fields.Char(string="Nombre del Archivo")
    periodo_fiscal = fields.Integer(
        string="Año Fiscal de Referencia",
        default=lambda self: fields.Date.today().year,
        required=True,
        help="Año fiscal al que corresponden las deducciones (ej: 2026).",
    )
    auto_apply = fields.Boolean(
        string="⚡ Aplicar inmediatamente a la Ficha del Empleado",
        default=True,
        help="Si está activado, actualiza automáticamente las cargas de familia (cónyuge, hijos) y la deducción mensual estimada en el empleado.",
    )
    state = fields.Selection(
        [("choose", "Seleccionar Archivo"), ("done", "Resultado de Importación")],
        default="choose",
    )
    result_summary = fields.Text(string="Resumen de Importación", readonly=True)

    def action_import_siradig(self):
        """Procesa el archivo subido (uno o varios XML) y muestra el resumen por empleado.

        @return Acción que reabre el asistente con el resultado.
        @throws UserError Archivo vacío, ZIP dañado o sin XML.
        """
        self.ensure_one()
        if not self.file_data:
            raise UserError("Debe seleccionar un archivo XML o ZIP para importar.")

        decoded = base64.b64decode(self.file_data)
        fname = (self.file_name or "").lower()

        xml_contents = []

        if fname.endswith(".zip") or zipfile.is_zipfile(io.BytesIO(decoded)):
            try:
                with zipfile.ZipFile(io.BytesIO(decoded)) as zf:
                    for name in zf.namelist():
                        if name.lower().endswith(".xml") and not name.startswith("__MACOSX"):
                            xml_bytes = zf.read(name)
                            xml_contents.append((name, xml_bytes))
            except Exception as e:
                raise UserError(f"Error al descomprimir el archivo ZIP: {e}")
        else:
            xml_contents.append((self.file_name or "siradig.xml", decoded))

        if not xml_contents:
            raise UserError("No se encontraron archivos XML válidos dentro del archivo subido.")

        imported_count = 0
        applied_count = 0
        skipped_count = 0
        log_lines = []

        for name, xml_data in xml_contents:
            try:
                res = self._process_single_xml(name, xml_data)
                if res.get("status") == "success":
                    imported_count += 1
                    if res.get("applied"):
                        applied_count += 1
                    log_lines.append(f"✅ {res['msg']}")
                else:
                    skipped_count += 1
                    log_lines.append(f"⚠️ {res['msg']}")
            except Exception as err:
                skipped_count += 1
                log_lines.append(f"❌ Error en '{name}': {err}")

        summary = (
            f"=== RESULTADO DE LA IMPORTACIÓN SIRADIG F.572 ===\n"
            f"• Archivos XML procesados: {len(xml_contents)}\n"
            f"• Declaraciones guardadas con éxito: {imported_count}\n"
            f"• Fichas de empleados actualizadas: {applied_count}\n"
            f"• Omitidos o con advertencia: {skipped_count}\n\n"
            f"DETALLE POR EMPLEADO:\n" + "\n".join(log_lines)
        )

        self.write({
            "state": "done",
            "result_summary": summary,
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [[False, "form"]],
            "target": "new",
        }

    def _process_single_xml(self, filename, raw_bytes):
        """Parsea un archivo XML de AFIP F.572 e impacta en la BD.

        Busca al empleado por CUIL (también en identificación o NIF), lee período, número de
        presentación, cargas de familia, deducciones y pagos a cuenta, y crea o reemplaza la declaración
        con ese período y número.

        @param filename Nombre del archivo (para los mensajes).
        @param raw_bytes Contenido del XML.
        @return dict {status: success / skipped / error, msg, applied}.

        @bug T9 (docs/revision.md): con *Aplicar inmediatamente*, importar una presentación vieja después
             de una nueva pisa la ficha con los datos viejos. Tampoco lee los otros empleadores.
        """
        # Intentar decodificar con distintos encodings comunes de AFIP
        text = None
        for enc in ["utf-8", "iso-8859-1", "windows-1252", "latin-1"]:
            try:
                text = raw_bytes.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if not text:
            return {"status": "error", "msg": f"{filename}: No se pudo decodificar el archivo (encoding no reconocido)."}

        # Limpiar posibles caracteres extra previos a <?xml
        idx = text.find("<")
        if idx > 0:
            text = text[idx:]

        try:
            root = ET.fromstring(text.encode("utf-8"))
        except Exception as e:
            return {"status": "error", "msg": f"{filename}: XML inválido ({e})."}

        def find_child_text(elem, tag_names, default=""):
            """Texto del primer hijo con alguno de esos nombres (sin espacio de nombres ni mayúsculas).

            @param elem Elemento padre.
            @param tag_names Nombres posibles de la etiqueta.
            @param default Valor si no está.
            @return Texto.
            """
            for child in elem:
                c_tag = child.tag.split("}")[-1].lower()
                for target in tag_names:
                    if c_tag == target.lower():
                        return (child.text or "").strip()
            return default

        def find_child_elem(elem, tag_names):
            """Primer hijo con alguno de esos nombres.

            @param elem Elemento padre.
            @param tag_names Nombres posibles de la etiqueta.
            @return Elemento o None.
            """
            for child in elem:
                c_tag = child.tag.split("}")[-1].lower()
                for target in tag_names:
                    if c_tag == target.lower():
                        return child
            return None

        # 1. Identificar datos del empleado
        empleado_elem = find_child_elem(root, ["empleado", "datosEmpleado", "titular"])
        cuit = ""
        nombre_emp = ""
        if empleado_elem is not None:
            cuit = find_child_text(empleado_elem, ["cuit", "cuil", "nroDoc", "cuitEmpleado"])
            ap = find_child_text(empleado_elem, ["apellido", "ape"])
            nom = find_child_text(empleado_elem, ["nombre", "nom"])
            nombre_emp = f"{ap} {nom}".strip()

        if not cuit:
            cuit = find_child_text(root, ["cuit", "cuitEmpleado", "cuil"])

        clean_cuit = re.sub(r"\D", "", cuit or "")
        if not clean_cuit:
            return {"status": "skipped", "msg": f"{filename}: No se encontró CUIT de empleado en el archivo."}

        # Buscar empleado en Odoo
        Employee = self.env["hr.employee"]
        employee = Employee.search([("cuil", "like", clean_cuit)], limit=1)
        if not employee:
            # Buscar en identification_id o vat
            employee = Employee.search([("identification_id", "like", clean_cuit)], limit=1)
        if not employee:
            employee = Employee.search([("vat", "like", clean_cuit)], limit=1)

        if not employee:
            # Formato con guiones XX-XXXXXXXX-X
            if len(clean_cuit) == 11:
                formatted = f"{clean_cuit[:2]}-{clean_cuit[2:10]}-{clean_cuit[10]}"
                employee = Employee.search(["|", ("cuil", "=", formatted), ("identification_id", "=", formatted)], limit=1)

        if not employee:
            return {
                "status": "skipped",
                "msg": f"CUIT {clean_cuit} ({nombre_emp or 'Sin nombre'}): Empleado no existe en Odoo. Debe darlo de alta antes de importar su F.572.",
            }

        # 2. Período y número de presentación
        periodo_str = find_child_text(root, ["periodo", "periodoFiscal", "anio"], str(self.periodo_fiscal))
        try:
            periodo = int(periodo_str)
        except ValueError:
            periodo = self.periodo_fiscal

        nro_pres_str = find_child_text(root, ["nroPresentacion", "presentacionNro", "envio", "nroEnvio"], "1")
        try:
            nro_pres = int(nro_pres_str)
        except ValueError:
            nro_pres = 1

        fecha_str = find_child_text(root, ["fechaPresentacion", "fecha"], fields.Date.today().strftime("%Y-%m-%d"))
        # Extraer solo la fecha si viene con hora
        fecha_pres = fields.Date.today()
        if fecha_str:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", fecha_str)
            if match:
                try:
                    fecha_pres = fields.Date.to_date(match.group(1))
                except Exception:
                    pass

        # 3. Cargas de Familia
        cargas_vals = []
        cargas_elem = find_child_elem(root, ["cargasFamilia", "cargasDeFamilia", "familiares"])
        if cargas_elem is not None:
            for c_node in cargas_elem:
                c_tag = c_node.tag.split("}")[-1].lower()
                if c_tag in ["cargafamilia", "familiar", "carga"]:
                    parentesco_raw = find_child_text(c_node, ["parentesco", "tipo", "tipoFam"], "3")
                    # Normalizar parentesco según AFIP: 1=Cónyuge, 3 o 30=Hijo, 31=Hijo Incapacitado
                    if parentesco_raw in ["1", "conyuge"]:
                        p_code = "1"
                    elif parentesco_raw in ["31", "discapacitado", "incapacitado"]:
                        p_code = "31"
                    elif parentesco_raw in ["3", "30", "hijo", "hijastro"]:
                        p_code = "3"
                    else:
                        p_code = "99"

                    doc_c = find_child_text(c_node, ["nroDoc", "cuil", "documento", "cuit"])
                    ap_c = find_child_text(c_node, ["apellido", "ape"])
                    nom_c = find_child_text(c_node, ["nombre", "nom"])
                    m_desde = int(find_child_text(c_node, ["mesDesde", "desdeMes"], "1") or 1)
                    m_hasta = int(find_child_text(c_node, ["mesHasta", "hastaMes"], "12") or 12)
                    pct_str = find_child_text(c_node, ["porcentajeDeduccion", "porcentaje", "pct"], "100")
                    pct = float(str(pct_str).replace(",", ".")) if pct_str else 100.0

                    cargas_vals.append((0, 0, {
                        "parentesco": p_code,
                        "tipo_doc": find_child_text(c_node, ["tipoDoc"], "80"),
                        "nro_doc": doc_c,
                        "apellido": ap_c,
                        "nombre": nom_c,
                        "mes_desde": min(max(m_desde, 1), 12),
                        "mes_hasta": min(max(m_hasta, 1), 12),
                        "porcentaje_deduccion": pct,
                    }))

        # 4. Deducciones Generales
        deducciones_vals = []
        ded_map = {
            "1": "prepaga",
            "2": "seguro_vida",
            "3": "donaciones",
            "4": "interes_hipotecario",
            "5": "sepelio",
            "7": "alquiler",
            "8": "servicio_domestico",
            "10": "gastos_medicos",
            "12": "gastos_educacion",
            "13": "viaticos",
            "14": "indumentaria",
        }

        ded_elem = find_child_elem(root, ["deducciones", "otrasDeducciones"])
        if ded_elem is not None:
            for d_node in ded_elem:
                d_tag = d_node.tag.split("}")[-1].lower()
                if d_tag in ["deduccion", "item", "gasto"]:
                    tipo_cod = find_child_text(d_node, ["tipo", "codigoTipo", "codigo"], "otro")
                    tipo_nom = ded_map.get(tipo_cod, "otro")

                    monto_str = find_child_text(d_node, ["montoTotal", "monto", "total"], "0")
                    monto_float = float(str(monto_str).replace(",", ".")) if monto_str else 0.0

                    desc = find_child_text(d_node, ["denominacion", "descripTipo", "prestador", "concepto", "descripcion"])
                    cuit_prov = find_child_text(d_node, ["cuitDocProv", "cuitPrestador", "cuitLocador", "cuit"])

                    deducciones_vals.append((0, 0, {
                        "tipo_codigo": tipo_cod,
                        "tipo_nombre": tipo_nom,
                        "descripcion": desc or tipo_nom,
                        "cuit_prestador": cuit_prov,
                        "monto_total": max(0.0, monto_float),
                    }))

        # 5. Pagos a Cuenta
        pagos_vals = []
        pagos_elem = find_child_elem(root, ["retPerPagos", "pagosACuenta", "percepciones"])
        if pagos_elem is not None:
            for p_node in pagos_elem:
                p_tag = p_node.tag.split("}")[-1].lower()
                if p_tag in ["retperpago", "pagoacuenta", "percepcion"]:
                    monto_p_str = find_child_text(p_node, ["montoTotal", "monto"], "0")
                    monto_p = float(str(monto_p_str).replace(",", ".")) if monto_p_str else 0.0
                    pagos_vals.append((0, 0, {
                        "tipo": find_child_text(p_node, ["tipo", "codigo"], "Percepción RG"),
                        "descripcion": find_child_text(p_node, ["descripcion", "agente"]),
                        "monto_total": max(0.0, monto_p),
                    }))

        # 6. Guardar en Base de Datos (Crear o Actualizar F.572)
        SiradigModel = self.env["hr.siradig.f572"]
        domain = [
            ("employee_id", "=", employee.id),
            ("periodo_fiscal", "=", periodo),
            ("nro_presentacion", "=", nro_pres),
        ]
        existing = SiradigModel.search(domain, limit=1)

        vals = {
            "employee_id": employee.id,
            "cuit_empleado": clean_cuit,
            "periodo_fiscal": periodo,
            "nro_presentacion": nro_pres,
            "fecha_presentacion": fecha_pres,
            "xml_filename": filename,
            "xml_raw_content": text,
        }

        if existing:
            # Reemplazar líneas hijas
            existing.cargas_familia_ids.unlink()
            existing.deduccion_ids.unlink()
            existing.pago_cuenta_ids.unlink()
            vals["cargas_familia_ids"] = cargas_vals
            vals["deduccion_ids"] = deducciones_vals
            vals["pago_cuenta_ids"] = pagos_vals
            existing.write(vals)
            f572_rec = existing
        else:
            vals["cargas_familia_ids"] = cargas_vals
            vals["deduccion_ids"] = deducciones_vals
            vals["pago_cuenta_ids"] = pagos_vals
            f572_rec = SiradigModel.create(vals)

        applied = False
        if self.auto_apply:
            f572_rec.action_apply_to_employee()
            applied = True

        msg = (
            f"Empleado: '{employee.name}' (CUIL {clean_cuit}) | "
            f"Período: {periodo} (Envío #{nro_pres}) | "
            f"Cargas: {f572_rec.cargas_resumen} | "
            f"Deducciones: $ {f572_rec.total_deducciones_anual:,.2f} "
            f"({'Aplicado' if applied else 'Sin aplicar'})"
        )
        return {"status": "success", "msg": msg, "applied": applied}
