# Conceptos de Odoo que usa el módulo

Lo mínimo para leer el código, con enlaces a la documentación oficial de Odoo 19 y de OCA.

## Nómina de OCA (`payroll`)

Odoo Community no trae nómina; el módulo se apoya en [`payroll` de OCA](https://github.com/OCA/payroll).

| Pieza | Modelo | En este módulo |
|---|---|---|
| Recibo | `hr.payslip` | Un empleado en un período. `compute_sheet()` evalúa las reglas y crea las líneas (`hr.payslip.line`). |
| Lote | `hr.payslip.run` | Recibos de un mismo período y tipo. El asistente `hr.payslip.employees` genera los recibos. |
| Estructura | `hr.payroll.structure` | Lista de reglas (puede heredar de una estructura padre). |
| Regla salarial | `hr.salary.rule` | Condición y fórmula en Python, ejecutadas con `safe_eval`. Variables: `contract`, `employee`, `payslip`, `categories`, `rules`, `inputs`, `worked_days`, `payroll` y las que agrega el módulo (`inp`). |
| Categoría | `hr.salary.rule.category` | Agrupa reglas; `categories.REM` es la suma de la categoría hasta la regla actual. |
| Entrada | `hr.rule.input` / `hr.payslip.input` | Declaración de una novedad en la regla / su valor en el recibo. |
| Días trabajados | `hr.payslip.worked_days` | Días y horas del calendario y ausencias. Informativo en este módulo. |

Resultado de una regla: `result` (importe unitario) × `result_qty` (cantidad) × `result_rate` (%) / 100.

## Contrato = versión (Odoo 19)

En Odoo 19 el contrato es una **versión del empleado** (`hr.version`): sueldo, estructura, calendario y
fechas viven en la versión vigente, y muchos campos se editan desde el empleado. El código del módulo
sigue diciendo `contract` (`slip.contract_id` es un `hr.version`).

## ORM

- **Herencia** (`_inherit`): agrega campos y métodos a modelos existentes (recibo, lote, contrato,
  compañía). [ORM](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html).
- **Campos calculados** (`compute=`, `store=True`, `@api.depends`): los totales del recibo se guardan y se
  recalculan cuando cambian las líneas.
- **Onchange** (`@api.onchange`): sólo en el formulario (tipo de salario → estructura y calendario).
- **Restricciones** (`@api.constrains`): impiden guardar datos incoherentes (tipo de salario vs.
  estructura, CUIL inválido).
- **Datos XML** (`data/`): reglas, estructuras y tablas se cargan desde XML. Con `noupdate="0"` se
  reescriben al actualizar; con `noupdate="1"`, no.
  [Datos](https://www.odoo.com/documentation/19.0/developer/reference/backend/data.html).
- **Migraciones** (`migrations/<versión>/post-migrate.py`): corren al actualizar a esa versión.

## Recursos y ausencias

- **Calendario** (`resource.calendar`): franjas por día de la semana (`attendance_ids`), horas por día.
- **Feriados**: ausencias globales del calendario (`resource.calendar.leaves` sin recurso).
- **Licencias** (`hr.leave`, módulo `hr_holidays`): las aprobadas (`validate`) de tipo vacaciones dan
  `VAC_DIAS`.
- **Asistencias** (`hr.attendance`, módulo `hr_attendance`): fichadas de entrada y salida; el motor de
  horas extras (`hr.attendance.overtime.line` y sus reglas) clasifica el exceso.

## Permisos

Odoo controla el acceso en tres capas ([Security in Odoo](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)). Qué se configuró en este
módulo y para quién: [Seguridad](seguridad.md).

| Capa | Qué decide | En el módulo |
|---|---|---|
| [Permisos de acceso](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html#access-rights) (`ir.model.access`) | Si un grupo puede leer, escribir, crear o borrar **un modelo**. | `security/ir.model.access.csv`; tabla en la [referencia](referencia.md#permisos-por-modelo). |
| [Reglas de registro](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html#record-rules) (`ir.rule`) | **Qué registros** de ese modelo ve o modifica. | `security/payroll_arg_security.xml`. |
| [Acceso a campos](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html#field-access) (`groups=` en el campo) | Si un grupo ve **un campo**; si no, el campo desaparece de las vistas y leerlo da `AccessError`. | CBU y datos de Ganancias del empleado. |

### Cómo se evalúa una regla de registro

```xml
<field name="domain_force">['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]</field>
```

El `domain_force` es un [dominio](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#reference-orm-domains): una lista de condiciones
`(campo, operador, valor)`; `'|'` delante de dos condiciones es un "o".

- **Lo que está entre comillas a la izquierda es un campo** del registro filtrado (`company_id` del
  acumulador). Puede ser un camino: `payslip_id.company_id` (la compañía del recibo de la novedad).
- **Lo que está sin comillas a la derecha son variables** que arma Odoo al evaluar la regla, en
  `ir.rule._eval_context()` (`odoo/addons/base/models/ir_rule.py`):

| Variable | Valor |
|---|---|
| `user` | El usuario actual (`user.id`, `user.employee_id`…). |
| `company_ids` | Las compañías **tildadas** en el selector de compañías, filtradas por las permitidas en la ficha del usuario. |
| `company_id` | La compañía activa. |

- **Regla global** (sin grupos, `global = True`): se aplica a todos y se combina con **y** con las demás;
  las reglas **de grupo** se combinan con **o** entre sí
  ([global y de grupo](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html#global-rules-versus-group-rules)). Por eso el administrador de
  nómina ve "todo" (`[(1, '=', 1)]`) pero sólo de sus compañías.
- El superusuario (`sudo()`) no tiene reglas: los tests preparan datos con él y prueban con
  `self.env(user=…)` (ver [Tests](tests.md#probar-permisos)).
