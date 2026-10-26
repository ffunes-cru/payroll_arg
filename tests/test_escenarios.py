"""@file
Los escenarios de la guía de usuario cargan, reproducen los recibos reales y coinciden con
docs/usuario/resultados.md."""
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..tools.escenarios import ARCHIVO_RESULTADOS, _recibo, cargar, ejecutar, generar_resultados


@tagged("post_install", "-at_install")
class TestEscenarios(TransactionCase):
    """Ver tools/escenarios.py y docs/usuario/escenarios.md."""

    @classmethod
    def setUpClass(cls):
        """Carga los datos maestros y hace los ocho ejercicios una sola vez."""
        super().setUpClass()
        cargar(cls.env)
        cls.lotes = ejecutar(cls.env)

    def _lineas(self, numero, clave):
        """Importes por código del recibo de un empleado en un ejercicio.

        @param numero Número de ejercicio.
        @param clave Clave del empleado.
        @return dict {código: importe redondeado}.
        """
        lote = dict(self.lotes)[numero]
        return {line.code: round(abs(line.total), 2) for line in _recibo(lote, clave).line_ids if line.total}

    def test_resultados_actualizados(self):
        """docs/usuario/resultados.md coincide con el cálculo actual."""
        self.assertEqual(
            ARCHIVO_RESULTADOS.read_text(encoding="utf-8"), generar_resultados(self.env, self.lotes),
            "docs/usuario/resultados.md está desactualizado: regenerarlo como indica tools/escenarios.py.")

    def test_a_reproduce_recibos_reales(self):
        """El empleado A reproduce los dos recibos reales (2° Quincena agosto y 1° Quincena septiembre),
        con la base de septiembre tomada sola de agosto."""
        q2 = self._lineas(2, "a")
        self.assertEqual((q2["BASIC_HORAS"], q2["FERIADO"], q2["ADIC_ANTIG"], q2["RET_OS"], q2["COMP_JUB"]),
                         (587429.92, 60078.06, 38850.48, 35415.28, 42417.50))
        q1 = self._lineas(5, "a")
        self.assertEqual((q1["BASIC_HORAS"], q1["ADIC_ANTIG"], q1["RET_JUB"], q1["COMP_ART"], q1["COMP_OS"]),
                         (587429.92, 35245.80, 123822.68, 131058.03, 20266.71))

    def test_no_se_cargan_dos_veces(self):
        """Cargar los escenarios en una base que ya los tiene avisa en lugar de duplicar."""
        with self.assertRaises(UserError):
            cargar(self.env)
