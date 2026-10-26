"""@file
Permisos por perfil: quién ve los menús, los datos sensibles del empleado y los datos de nómina, y
separación por compañía (ver docs/seguridad.md)."""
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSeguridad(TransactionCase):
    """Cinco perfiles sobre dos compañías:

    - interno: usuario de otra área, sin permisos de RR. HH. ni de nómina;
    - rrhh: Empleados / Oficial, sin nómina;
    - oficial: Nómina / Oficial, responsable del departamento D1 (no del D2);
    - liquidador: Nómina / Administrador de la compañía A;
    - liquidador_b: Nómina / Administrador de la compañía B.
    """

    @classmethod
    def setUpClass(cls):
        """Dos compañías, dos departamentos en A, un empleado por departamento con recibo calculado y
        F.572, y un empleado con recibo en B."""
        super().setUpClass()
        ref = cls.env.ref
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Compañía B"})
        both = (cls.company_a | cls.company_b).ids

        def usuario(login, grupos, companias):
            """Usuario de prueba.

            @param login Login.
            @param grupos xmlids de grupos.
            @param companias Compañías permitidas (la primera es la actual).
            @return res.users.
            """
            return cls.env["res.users"].with_context(no_reset_password=True).create({
                "name": login, "login": login, "company_id": companias[0], "company_ids": [(6, 0, companias)],
                "group_ids": [(6, 0, [ref(g).id for g in grupos])],
            })

        cls.interno = usuario("seg_interno", ["base.group_user"], [cls.company_a.id])
        cls.rrhh = usuario("seg_rrhh", ["base.group_user", "hr.group_hr_user"], [cls.company_a.id])
        cls.oficial = usuario("seg_oficial", ["base.group_user", "payroll.group_payroll_user"], [cls.company_a.id])
        cls.liquidador = usuario("seg_liquidador", ["base.group_user", "payroll.group_payroll_manager"], [cls.company_a.id])
        cls.liquidador_b = usuario("seg_liquidador_b", ["base.group_user", "payroll.group_payroll_manager"],
                                   [cls.company_b.id])
        cls.admin_ambas = usuario("seg_admin_ambas", ["base.group_user", "payroll.group_payroll_manager"], both)

        Department = cls.env["hr.department"]
        cls.d1 = Department.create({"name": "D1", "manager_id": cls.env["hr.employee"].create(
            {"name": "Jefe D1", "user_id": cls.oficial.id}).id})
        cls.d2 = Department.create({"name": "D2"})
        cls.emp_d1 = cls._empleado("Empleado D1", cls.company_a, cls.d1, "20301112220")
        cls.emp_d2 = cls._empleado("Empleado D2", cls.company_a, cls.d2, "20402223333")
        cls.emp_b = cls._empleado("Empleado B", cls.company_b, False, "20384445552")
        cls.lote_a = cls._lote(cls.company_a, cls.emp_d1 | cls.emp_d2)
        cls.lote_b = cls._lote(cls.company_b, cls.emp_b)
        for empleado in cls.emp_d1 | cls.emp_d2 | cls.emp_b:
            cls.env["hr.siradig.f572"].create({
                "employee_id": empleado.id, "cuit_empleado": empleado.cuil, "company_id": empleado.company_id.id,
                "deduccion_ids": [(0, 0, {"tipo_nombre": "prepaga", "monto_total": 1200000.0})],
            })

    @classmethod
    def _empleado(cls, nombre, compania, departamento, cuil):
        """Mensualizado con sueldo alto (para que haya acumulador de Ganancias) y datos sensibles.

        @param nombre Nombre.
        @param compania Compañía.
        @param departamento Departamento o False.
        @param cuil CUIL válido.
        @return hr.employee.
        """
        ref = cls.env.ref
        return cls.env["hr.employee"].with_company(compania).create({
            "name": nombre, "company_id": compania.id, "department_id": departamento and departamento.id,
            "cuil": cuil, "cbu": "0110000330000000000000", "ganancias_hijos": 1,
            "ganancias_otras_deducciones_mensual": 100000.0, "aporte_adicional_ss_monto": 5000.0,
            "contract_date_start": "2020-01-01", "date_version": "2020-01-01", "is_convencionado": False,
            "wage": 3000000.0, "wage_type": "monthly", "schedule_pay": "monthly",
            "struct_id": ref("payroll_arg.structure_mensual_arg").id,
            "resource_calendar_id": ref("payroll_arg.resource_calendar_mensual_40h").id,
        })

    @classmethod
    def _lote(cls, compania, empleados):
        """Lote mensual de agosto 2026 calculado, con un valor de lote.

        @param compania Compañía del lote.
        @param empleados Empleados.
        @return hr.payslip.run.
        """
        env = cls.env(context=dict(cls.env.context, allowed_company_ids=[compania.id]))
        lote = env["hr.payslip.run"].create({
            "name": f"Mensual {compania.name}", "tipo_liquidacion": "Mensual", "company_id": compania.id,
            "date_start": "2026-08-01", "date_end": "2026-08-31",
        })
        lote._onchange_tipo_liquidacion()
        env["hr.payslip.run.novelty"].create({
            "run_id": lote.id, "amount": 1000.0,
            "input_id": env["hr.rule.input"].search([("code", "=", "PRESENTISMO")], limit=1).id,
        })
        contexto = {"active_id": lote.id, "active_model": "hr.payslip.run"}
        env["hr.payslip.employees"].with_context(**contexto).create(
            {"employee_ids": [(6, 0, empleados.ids)]}).compute_sheet()
        lote.slip_ids.compute_sheet()
        return lote

    def _visible(self, usuario, modelo, registros):
        """Registros de `registros` que el usuario puede leer.

        @param usuario res.users.
        @param modelo Nombre del modelo.
        @param registros Recordset (como superusuario).
        @return Recordset filtrado por las reglas del usuario (vacío si no tiene acceso).
        """
        try:
            return self.env(user=usuario)[modelo].search([("id", "in", registros.ids)])
        except AccessError:
            return self.env[modelo]

    # ── S1: menús ──

    def test_s1_menu_nomina_solo_para_nomina(self):
        """El menú Nómina Argentina (y con él la app) no aparece a quien no es de nómina."""
        menu = self.env.ref("payroll_arg.menu_payroll_arg_root")
        for usuario in (self.interno, self.rrhh):
            self.assertNotIn(menu.id, self.env(user=usuario)["ir.ui.menu"]._visible_menu_ids(), usuario.login)
        self.assertIn(menu.id, self.env(user=self.oficial)["ir.ui.menu"]._visible_menu_ids())

    # ── S2: datos sensibles del empleado ──

    def test_s2_rrhh_ve_cuil_pero_no_cbu_ni_ganancias(self):
        """RR. HH. lee el CUIL; el CBU, las cargas y deducciones de Ganancias, el aporte adicional y el
        F.572 son sólo de nómina. El formulario del empleado abre sin esos campos."""
        empleado = self.env(user=self.rrhh)["hr.employee"].browse(self.emp_d1.id)
        self.assertEqual(empleado.cuil, "20301112220")
        for campo in ("cbu", "ganancias_hijos", "ganancias_otras_deducciones_mensual", "aporte_adicional_ss_monto",
                      "siradig_count"):
            with self.assertRaises(AccessError, msg=campo):
                empleado.read([campo])
        arch = self.env(user=self.rrhh)["hr.employee"].get_view(self.env.ref("hr.view_employee_form").id)["arch"]
        self.assertNotIn("siradig", arch)
        self.assertNotIn("ganancias_", arch)
        self.assertEqual(self.env(user=self.oficial)["hr.employee"].browse(self.emp_d1.id).cbu, "0110000330000000000000")

    # ── S3: el oficial de nómina ve lo de su departamento ──

    def test_s3_oficial_ve_solo_su_departamento(self):
        """El oficial ve recibos, novedades, líneas, acumuladores de Ganancias y F.572 de su departamento,
        no los del otro; el administrador de nómina ve los dos."""
        datos = {
            "hr.payslip": self.lote_a.slip_ids,
            "hr.payslip.input": self.lote_a.slip_ids.input_line_ids,
            "hr.payslip.line": self.lote_a.slip_ids.line_ids,
            "hr.ganancias.accumulator": self.env["hr.ganancias.accumulator"].search(
                [("employee_id", "in", (self.emp_d1 | self.emp_d2).ids)]),
            "hr.siradig.f572": self.env["hr.siradig.f572"].search(
                [("employee_id", "in", (self.emp_d1 | self.emp_d2).ids)]),
            "hr.siradig.deduccion": self.env["hr.siradig.f572"].search(
                [("employee_id", "in", (self.emp_d1 | self.emp_d2).ids)]).deduccion_ids,
        }
        for modelo, registros in datos.items():
            def empleado(registro):
                """Empleado de un registro (las deducciones lo tienen en su F.572)."""
                return registro.f572_id.employee_id if "f572_id" in registro._fields else registro.employee_id
            self.assertTrue(registros.filtered(lambda r: empleado(r) == self.emp_d2), modelo)
            vistos = self._visible(self.oficial, modelo, registros)
            self.assertTrue(vistos, modelo)
            self.assertEqual({empleado(r).id for r in vistos}, {self.emp_d1.id}, modelo)
            self.assertEqual(self._visible(self.liquidador, modelo, registros), registros, modelo)

    # ── S6: la configuración la cambia el administrador ──

    def test_s6_configuracion_solo_administrador(self):
        """El oficial lee convenios, categorías y escalas de Ganancias pero no los cambia, ni actualiza
        sueldos en masa; el administrador sí."""
        oficial = self.env(user=self.oficial)
        categoria = self.env.ref("payroll_arg.afip_cat_uom_operario")
        for registro in (self.env.ref("payroll_arg.afip_cct_uom"), categoria,
                         self.env.ref("payroll_arg.scale_ganancias_2026")):
            self.assertTrue(oficial[registro._name].browse(registro.id).name)
            with self.assertRaises(AccessError, msg=registro._name):
                oficial[registro._name].browse(registro.id).write({"name": "cambiado"})
        with self.assertRaises(AccessError):
            oficial["afip.labor.category"].browse(categoria.id).action_update_contract_wages()
        self.env(user=self.liquidador)["afip.cct"].browse(self.env.ref("payroll_arg.afip_cct_uom").id).write(
            {"union_rate": 2.5})
