# Tests: cómo están hechos y cómo leerlos

Los tests son la red de seguridad del módulo: cada arreglo de la [revisión](revision.md) entra con el
test que reproduce el problema, y cada paso de la [guía de usuario](usuario/guia.md) tiene el suyo.
Esta página explica la sintaxis para poder leerlos y escribir nuevos.

Documentación oficial: [Testing Odoo](https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html#testing-python-code)
y [ORM](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html).

## Qué hay

| Archivo | Prueba |
|---|---|
| `tests/test_recibos_referencia.py` | Los dos recibos de referencia UOM, al centavo. |
| `tests/test_novedades.py` | La carga de novedades (calendario, lote, CSV) y el cálculo de quincenas y meses. |
| `tests/test_escenarios.py` | Los escenarios de la guía y que `docs/usuario/resultados.md` siga al cálculo. |
| `tests/test_guia_usuario.py` | La guía de usuario paso a paso, con `Form` (como la interfaz). |
| `tests/test_seguridad.py` | Qué ve cada perfil y cada compañía ([Seguridad](seguridad.md)). |
| `tests/test_documentacion.py` | Que todo el código esté documentado y que `docs/referencia.md` esté al día. |
| `payroll_arg_attendance/tests/` | Horas desde fichadas y documentación del módulo de asistencias. |

## Anatomía de un test

```python
from odoo.exceptions import AccessError
from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")      # (1)
class TestSeguridad(TransactionCase):       # (2)
    """Qué prueba la clase."""

    @classmethod
    def setUpClass(cls):                    # (3)
        super().setUpClass()
        cls.empleado = cls.env["hr.employee"].create({"name": "X"})

    def test_rrhh_no_ve_el_cbu(self):       # (4)
        """Qué prueba este método (sale en el log)."""
        with self.assertRaises(AccessError):  # (5)
            self.env(user=self.rrhh)["hr.employee"].browse(self.empleado.id).read(["cbu"])
```

1. **Etiquetas** ([tags](https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html#reference-testing-tags)):
   `post_install` corre el test con todos los módulos instalados; `-at_install` lo saca de la
   instalación. Así ven las vistas y reglas de `payroll_arg_attendance` y de OCA.
2. **`TransactionCase`**: cada test corre en una transacción que se **deshace** al terminar. Nada de
   lo que crea queda en la base, y los tests no dependen del orden.
3. **`setUpClass`**: prepara los datos **una vez** para todos los tests de la clase (empleados, lotes,
   usuarios). Quedan como `cls.xxx` / `self.xxx`.
4. **Métodos `test_…`**: cada uno es un test. El docstring dice qué se prueba, en una oración.
5. **Aserciones** de `unittest`:

| Aserción | Falla si… |
|---|---|
| `self.assertTrue(x, msg)` / `assertFalse` | `x` es falso / verdadero. Un recordset vacío es falso. |
| `self.assertEqual(a, b, msg)` | `a != b`. |
| `self.assertAlmostEqual(a, b, places=2)` | Difieren en más de un centavo (importes). |
| `self.assertIn(a, b)` / `assertNotIn` | `a` no está / está en `b`. |
| `with self.assertRaises(UserError):` | El bloque **no** lanza ese error. |

El último argumento (`msg`) se muestra si falla: conviene pasar el código del concepto o el modelo.

## Lo que más se usa del ORM

| Expresión | Qué hace | Documentación |
|---|---|---|
| `self.env` | El entorno: usuario, compañía, contexto. En los tests es el superusuario (sin reglas). | [Environment](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#reference-orm-environment) |
| `self.env["hr.payslip"]` | El modelo (recordset vacío): para buscar o crear. | [Recordsets](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#recordsets) |
| `.create({...})`, `.write({...})` | Crear / modificar registros. | [CRUD](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#reference-orm-models-crud) |
| `.search([("campo", "=", valor)])` | Buscar con un **dominio**: lista de condiciones `(campo, operador, valor)`; `'|'` antes de dos condiciones es un "o". | [Dominios](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#reference-orm-domains) |
| `lote.slip_ids.input_line_ids` | Seguir un campo sobre varios registros une los resultados (todas las novedades de todos los recibos). | [Operaciones](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#reference-orm-records-operations) |
| `.filtered(lambda l: l.code == "RET_JUB")` | Filtrar en memoria. | ídem |
| `.mapped("total")` | Lista de valores de un campo. | ídem |
| `self.env.ref("payroll_arg.afip_cct_uom")` | Un registro por su xmlid (el `id` de los XML de `data/`). | [Datos](https://www.odoo.com/documentation/19.0/developer/reference/backend/data.html) |
| `self.env(user=usuario)` | El mismo entorno **como otro usuario**: se aplican sus permisos y reglas. | [Alterar el entorno](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#altering-the-environment) |
| `.with_context(clave=valor)` | El entorno con un contexto distinto (p. ej. `active_id` de un asistente). | ídem |

## `Form`: probar como la interfaz

```python
form = Form(self.env["hr.payslip"])       # formulario nuevo, con su vista
form.employee_id = empleado                # dispara los onchange, como al elegir en pantalla
form.date_from = "2026-08-01"
recibo = form.save()
```

`Form` (de `odoo.tests`) carga la vista real y respeta lo que la interfaz hace:
- ejecuta los **onchange** al asignar cada campo, en el orden en que se asignan;
- **no deja escribir** campos invisibles ni de sólo lectura (`AssertionError: can't write on readonly
  field`), igual que la pantalla;
- `with form.lineas.new() as linea:` / `.edit(i)` para las tablas (one2many).

Por eso `test_guia_usuario.py` usa `Form` y no `create`: los errores G1 y G5 sólo aparecían con el
formulario. Un selector de rango de fechas no se puede manejar con `Form`: esas fechas entran por
contexto (`default_date_start`).

## Probar permisos

```python
def _visible(self, usuario, modelo, registros):
    try:
        return self.env(user=usuario)[modelo].search([("id", "in", registros.ids)])
    except AccessError:
        return self.env[modelo]
```

`search` como el usuario devuelve sólo lo que sus **reglas de registro** le dejan ver; si ni siquiera
tiene **permiso de acceso** al modelo, Odoo lanza `AccessError` y se cuenta como "no ve nada". Cómo se
evalúan las reglas (y de dónde salen `user` y `company_ids`): [Conceptos de Odoo › Permisos](odoo.md#permisos).

## Correr los tests

```bash
# Todos los de los dos módulos (actualiza el módulo antes)
.venv/bin/python odoo-bin -d claude_pa_fresh -u payroll_arg,payroll_arg_attendance \
    --test-tags /payroll_arg,/payroll_arg_attendance --stop-after-init --http-port=8092

# Una clase o un método
--test-tags /payroll_arg:TestSeguridad
--test-tags /payroll_arg:TestSeguridad.test_s7_cada_compania_ve_lo_suyo
```

El log termina con `0 failed, 0 error(s) of N tests`. Un fallo muestra archivo, línea, valor esperado
contra obtenido y el mensaje. Ver [Running tests](https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html#running-tests).

## Escribir uno nuevo

1. Elegir el archivo por tema (tabla de arriba) o crear `tests/test_<tema>.py` e importarlo en
   `tests/__init__.py`.
2. Para un arreglo: **primero el test**, correrlo y ver que **falla** con el código actual; después el
   arreglo.
3. Datos mínimos en `setUpClass`; con `Form` si se prueba algo que hace el usuario en pantalla.
4. Docstring en la clase y en cada método (lo exige `test_documentacion` en el resto del código y lo
   lee quien revisa).
