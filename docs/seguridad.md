# Seguridad: quién ve qué

Los permisos combinan los grupos de `payroll` (OCA), los de Empleados de Odoo y lo que agrega este
módulo:

- grupos en menús y campos;
- reglas por departamento;
- reglas por compañía.

`tests/test_seguridad.py` prueba cada perfil.

## Qué permiso darle a cada uno

| Persona | Permisos a asignar | Qué puede hacer |
|---|---|---|
| Usuario de otra área | Ninguno de *Haberes (Payroll)* | No ve la app de nómina ni datos de sueldos. En los empleados ve lo público. |
| RR. HH. | *Empleados: Oficial* o *Administrador* | Fichas y contratos, con el CUIL. No ve CBU, datos de Ganancias, F.572, sueldos ni recibos. |
| **Liquidador** | ***Haberes: Administrador*** | Todo lo de nómina de sus compañías: lotes, recibos, novedades, Ganancias, F.572, configuración. |
| Oficial de nómina | *Haberes: Oficial* | Recibos, novedades, líneas, acumuladores de Ganancias y F.572 sólo de los empleados de los departamentos que dirige, de él mismo o sin departamento. Configuración en lectura. **No puede usar lotes** (lo decide `payroll` de OCA). |

**Liquidador = Haberes: Administrador** (decisión D14): todo el circuito argentino trabaja con lotes, y
OCA sólo deja usar lotes al administrador. La separación entre liquidadores es por compañía.

> **Cuidado.** En `payroll` de OCA, cualquier permiso de *Haberes* da también *Empleados: Administrador*.
> Quien liquida puede administrar empleados. Se mantiene así (D14).

## Qué ve cada perfil

| Dato | Otra área | RR. HH. | Oficial de nómina | Liquidador |
|---|---|---|---|---|
| App *Haberes* y menú *Nómina Argentina* | — | — | sí | sí |
| Ficha del empleado, CUIL | lo público | sí | sí | sí |
| CBU, cargas y deducciones de Ganancias, aporte adicional, F.572 | — | — | sí | sí |
| Sueldo / valor hora del contrato | — | — | sí | sí |
| Recibos, novedades y líneas | — | — | su departamento | todos |
| Acumuladores de Ganancias | — | — | su departamento | todos |
| Lotes | — | — | — | todos |
| Convenios, categorías, tablas AFIP, escalas de Ganancias | — | — | lectura | lectura y escritura |
| *Actualizar Sueldos de Contratos* | — | — | — | sí |
| Alícuotas, tope, detracción, seguros (compañía) | — | — | — | sólo con *Ajustes* |

## Varias compañías

Todo dato de nómina queda en la compañía de su lote o su empleado:

- lotes, recibos, novedades, líneas y valores del lote;
- escalas y acumuladores de Ganancias;
- F.572.

Un usuario sólo ve los de las compañías que tiene habilitadas.

- **Parámetros:** alícuotas, tope, detracción, coeficientes y seguros son de cada compañía. Completarlos
  en cada una.
- **Escala de Ganancias:** el recibo usa la de **su** compañía. Cargar la escala en cada compañía (se
  puede duplicar y cambiar la compañía).
- **Estructuras salariales:** `payroll` (OCA) exige que cada estructura sea de una compañía. Cada compañía
  recibe su copia de las 8 estructuras argentinas al crearse (y al actualizar el módulo, si faltan). El
  empleado y el lote toman las de su compañía.
- **Compartido entre compañías:** reglas salariales y sus categorías, convenios, categorías laborales,
  tablas AFIP y calendarios del módulo. Un cambio en una regla o un convenio vale para todas.
- Un liquidador de varias compañías las habilita en su usuario y elige con el selector de compañía en
  cuál trabaja.

## Agregar un modelo con datos de nómina

Todo modelo nuevo que guarde datos de empleados o importes necesita:
1. permiso de acceso para *Haberes: Oficial* y/o *Administrador* (`security/ir.model.access.csv`);
2. regla de oficial / administrador si tiene empleado (`security/payroll_arg_security.xml`);
3. regla multi-compañía (por su compañía o la de su padre);
4. `groups="payroll.group_payroll_user"` en los campos sensibles que agregue a modelos de RR. HH.;
5. su caso en `tests/test_seguridad.py`.
