"""@file
La guía de usuario funciona tal como está escrita: cada paso se hace con `Form`, que reproduce lo que hace
la interfaz (onchanges, campos visibles y de sólo lectura) en lugar de escribir directo en los modelos."""
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGuiaUsuario(TransactionCase):
    """Sigue docs/usuario/guia.md con dos empleados cargados como dice la guía (sección 3.1): uno con
    fecha de inicio de contrato y otro sin ella."""

    @classmethod
    def setUpClass(cls):
        """Compañía con CUIT y los dos empleados dados de alta por formulario."""
        super().setUpClass()
        cls.env.company.cuit = "30712345679"
        cls.con_contrato = cls._alta("Guía Con Contrato", "20301112220", 7001, "2024-01-01")
        cls.sin_contrato = cls._alta("Guía Sin Contrato", "20402223333", 7002, False)

    @classmethod
    def _alta(cls, nombre, cuil, legajo, inicio):
        """Alta de un empleado como indica la guía, en la pestaña Nómina del formulario.

        @param nombre Nombre.
        @param cuil CUIL.
        @param legajo Legajo.
        @param inicio Fecha de inicio del contrato, o False para no cargarla.
        @return hr.employee.
        """
        form = Form(cls.env["hr.employee"])
        form.name = nombre
        form.cuil = cuil
        form.legajo = legajo
        form.cbu = "0110000330000000000000"
        if inicio:
            form.contract_date_start = inicio
        form.labor_category_id = cls.env.ref("payroll_arg.afip_cat_uom_operario")
        form.cct_id = cls.env.ref("payroll_arg.afip_cct_uom")
        return form.save()

    def _lote(self, tipo, desde, hasta):
        """Lote creado por formulario. El período se elige con el selector de rango, que `Form` no
        maneja: las fechas entran por contexto.

        @param tipo Tipo de liquidación.
        @param desde Inicio.
        @param hasta Fin.
        @return hr.payslip.run.
        """
        form = Form(self.env["hr.payslip.run"].with_context(default_date_start=desde, default_date_end=hasta))
        form.name = f"Guía {tipo}"
        form.tipo_liquidacion = tipo
        return form.save()

    def _generar(self, lote, empleados):
        """Botón Generar nóminas del lote.

        @param lote hr.payslip.run.
        @param empleados Empleados elegidos.
        """
        form = Form(self.env["hr.payslip.employees"].with_context(active_id=lote.id, active_model="hr.payslip.run"))
        for empleado in empleados:
            form.employee_ids.add(empleado)
        form.save().compute_sheet()

    # ── G1: recibo nuevo desde el formulario ──

    def test_g1_recibo_nuevo_por_formulario(self):
        """Un recibo nuevo desde Liquidaciones del empleado abre y calcula: el formulario elige el
        empleado antes que el contrato, y la antigüedad no puede romperse sin contrato."""
        for empleado in (self.sin_contrato, self.con_contrato):
            form = Form(self.env["hr.payslip"])
            form.employee_id = empleado
            form.date_from = "2026-08-01"
            form.date_to = "2026-08-15"
            recibo = form.save()
        self.assertEqual(recibo.contract_id, self.con_contrato.version_id)
        self.assertEqual(recibo.struct_id, self.env.ref("payroll_arg.structure_jornal_quincenal_arg"))
        self.assertEqual(recibo.antiguedad_anios, 2)
        recibo.compute_sheet()
        self.assertTrue(recibo.line_ids)

    # ── G4: empleado sin contrato en un lote ──

    def test_g4_lote_con_empleado_sin_contrato(self):
        """Generar un lote con un empleado sin contrato avisa quién es y dónde se corrige, antes de crear
        recibos; el lote no queda a medias."""
        lote = self._lote("1° Quincena", "2026-08-01", "2026-08-15")
        with self.assertRaises(UserError) as error:
            self._generar(lote, self.con_contrato | self.sin_contrato)
        self.assertIn("Guía Sin Contrato", str(error.exception))
        self.assertIn("Fecha de inicio del contrato", str(error.exception))
        self.assertFalse(lote.slip_ids)

    # ── G3: plantilla de alta masiva ──

    def test_g3_plantilla_de_empleados_se_importa(self):
        """La plantilla de alta masiva (sección 3.2) se puede importar tal cual: sus CUIL de ejemplo son
        válidos."""
        exportar = self.env["payroll.arg.employee.wizard"].create({"operation_mode": "export", "export_type": "template"})
        exportar.action_export_excel()
        importar = self.env["payroll.arg.employee.wizard"].create({
            "operation_mode": "import", "data_file": exportar.export_file, "filename": "plantilla.xlsx"})
        importar.action_import_file()
        self.assertIn("Empleados Creados: 2", importar.result_summary)
        self.assertNotIn("Errores", importar.result_summary)

    # ── T1: recargar el F.572 sin declaraciones ──

    def test_t1_recargar_siradig_sin_f572(self):
        """*Recargar desde Último F.572* sin declaraciones muestra el aviso, no un error de Python."""
        with self.assertRaises(UserError):
            self.con_contrato.action_reapply_latest_siradig()

    # ── F1: una sola pestaña Nómina ──

    def test_f1_una_sola_pestana_nomina(self):
        """El formulario del empleado tiene una sola pestaña de nómina, la estándar, con los datos
        argentinos y sin los campos que no se usan."""
        from lxml import etree
        arch = etree.fromstring(self.env["hr.employee"].get_view(self.env.ref("hr.view_employee_form").id)["arch"])
        self.assertFalse(arch.xpath("//page[@string='Nómina Argentina']"))
        pagina = arch.xpath("//page[@name='payroll_information']")[0]
        campos = [campo.get("name") for campo in pagina.iter("field")]
        for campo in ("contract_date_start", "wage_type", "wage", "struct_id", "resource_calendar_id", "cuil",
                      "legajo", "cct_id", "labor_category_id", "afip_situation_id", "afip_contract_type_id",
                      "aporte_adicional_ss_monto", "ganancias_hijos"):
            self.assertIn(campo, campos, campo)
        for campo in ("wage", "struct_id", "resource_calendar_id"):
            self.assertEqual(campos.count(campo), 1, campo)
        for campo in ("contract_type_id", "structure_type_id"):
            nodo = pagina.xpath(f".//field[@name='{campo}']")
            self.assertTrue(not nodo or nodo[0].get("invisible") in ("1", "True"), campo)
