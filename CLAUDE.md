# Nómina Argentina (`payroll_arg`) — guía para Claude

Este archivo es la fuente única de contexto y reglas de trabajo para agentes (GEMINI.md remite acá).
La documentación funcional y técnica está en `README.md` y `docs/`; leer antes de cambiar código:
`docs/conceptos.md`, `docs/liquidacion.md`, `docs/arquitectura.md`, `docs/flujos.md`,
`docs/revision.md` (problemas conocidos, ids C1, E1, T1…), `docs/decisiones.md` (D1…) y
`docs/pendientes.md` (preguntas abiertas, P1…). Guía de usuario y escenarios de prueba: `docs/usuario/`.

## Contexto

- Empresa metalúrgica de Córdoba. Liquida **jornalizados UOM** (CCT 260/75, valor hora, 1° y 2°
  quincena) y **mensualizados** (administración). También vacaciones, SAC, liquidación final y
  Ganancias 4ta categoría; exporta recibo PDF, Libro de Sueldos Digital, F.931 y bancos (Galicia,
  Santander).
- Odoo 19 Community + `payroll` de OCA. En Odoo 19 el contrato es `hr.version` (el código lo llama
  `contract`).
- **Todavía no hay datos de producción**: los datos de `mydb` son de prueba. Los cambios de esquema se
  resuelven con `-u` y, si hace falta, una migración simple; no mantener compatibilidad hacia atrás
  con código muerto.
- Referencia de verdad: dos recibos reales (1° Quincena sep-2026 y 2° Quincena ago-2026, valor hora
  $6.675,34, 6 años) reproducidos al centavo en `tests/test_recibos_reales.py`. Si un cambio los rompe,
  se frena y se consulta: no se ajusta el test para que pase.

## Decisiones de negocio confirmadas

Fuente única: `docs/decisiones.md` (se importa acá). No volver a discutirlas; si una norma parece
contradecirlas, señalarlo y preguntar. Las preguntas sin responder están en `docs/pendientes.md`
(P1, P2…): no implementar un hallazgo que dependa de una pregunta abierta.

@docs/decisiones.md

## Repositorios

| Repo | Ruta | Rama base | Notas |
|---|---|---|---|
| `ffunes-cru/payroll_arg` | `addons/payroll_arg` | `main` | Contiene el submódulo `payroll_arg_reportes`. |
| `ffunes-cru/payroll_arg_reportes` | `addons/payroll_arg/payroll_arg_reportes` | `develop` | Librería `py_arg_reports` (PDF, LSD, F.931, bancos). Publicar su commit **antes** que el puntero en `payroll_arg`. |
| `ffunes-cru/payroll_arg_attendance` | `addons/payroll_arg_attendance` | `main` | Depende de `payroll_arg`; se mergea después. |

El repo `odoo/` de afuera no versiona estos addons (aparecen sin seguimiento): no commitear ahí.

## Entorno

- Shell **fish**. Desde `~/odoo_sv/odoo`: `.venv/bin/python odoo-bin`, addons path
  `addons,odoo/addons`.
- Bases: `mydb` (desarrollo manual, empleado John Doe y sus lotes) y `claude_pa_fresh` (tests y
  referencia). No correr tests ni scripts que escriban sobre `mydb`.
- Python no se recarga solo: detener el servidor, `-u payroll_arg,payroll_arg_attendance`, arrancar.
- Comandos de tests, referencia y Doxygen: `docs/operacion.md#comandos-frecuentes`.
- Temporales en `$CLAUDE_JOB_DIR/tmp` (o el scratchpad), nunca en el repo.

## Forma de trabajo

- **Un PR por tema, un commit por hallazgo.** Cada PR agrupa ids relacionados de `docs/revision.md`
  (p. ej. "Vacaciones: C1, C13, C14, C16") y tiene un commit por id, para revisar commit por commit.
  Merge siempre con **"Create a merge commit"**: conserva los commits (y sus hashes) y el PR queda como una
  unidad que se puede revertir. Nunca squash ni "Rebase and merge": los dos crean commits nuevos, se
  pierde el commit por id y se rompe el puntero del submódulo.
- **Ramas:** `fix/<tema>` desde `main` actualizado. Si un PR depende de otro todavía abierto, se apila
  sobre su rama y se dice en la descripción. Nunca push a `main` ni `--force` sobre ramas ajenas.
- **No empezar el PR siguiente** sin que el usuario lo pida, salvo que lo haya autorizado para una serie.
- **Commits:** Conventional Commits en inglés con el id: `fix(payroll_arg): C1 do not pay vacations already
  paid in a vacation batch`. Cuerpo: qué estaba mal, norma o decisión, cómo se verificó.
- **Descripción del PR:** ids que resuelve, comportamiento antes / después con un ejemplo en pesos,
  decisiones de negocio que asume, tests agregados, documentación tocada y cómo probarlo a mano
  (escenario de la guía de usuario).
- **Por cada hallazgo:**
  1. Test de regresión que falle con el código actual (reproduce el caso de la revisión).
  2. Arreglo mínimo.
  3. Tests completos de los dos módulos en verde, recibos reales al centavo.
  4. Quitar el `@bug <id>` del código y el comentario `Ver <id>` de la regla; pasar el punto de
     `docs/revision.md` a "Resueltos" con el PR.
  5. Actualizar `docs/liquidacion.md` / `flujos.md` / `docs/usuario/` si cambia el comportamiento, y
     regenerar `docs/referencia.md` y `docs/usuario/resultados.md`.
- **Hallazgos de norma** (marcados *Norma* en la revisión): no implementar una interpretación legal
  sin confirmación. La pregunta va en `docs/pendientes.md` con la cita, un ejemplo en pesos y las
  opciones; cuando el usuario responde, pasa a `docs/decisiones.md` y recién ahí se corrige.
- **Escenarios de prueba** (`tools/escenarios.py`, `docs/usuario/`): si un cambio modifica un importe,
  regenerar `docs/usuario/resultados.md` en el mismo commit y actualizar el texto del ejercicio (quitar
  el "problema conocido" que se arregló). Un arreglo nuevo que se pueda ver en un ejercicio, agregarlo.

## Principios de código

- **La regla de negocio vive en un solo lugar.** Fórmulas en las reglas del XML; novedades automáticas en
  `hr.payslip._get_period_input_amounts()`; parámetros en `get_payroll_dict()`. El recibo, el PDF y las
  exportaciones leen las líneas calculadas, no recalculan (el pie del recibo hoy recalcula: C8).
- **Las novedades sólo en las entradas** (`inp('CÓDIGO')`); el cálculo nunca escribe entradas ni otros
  modelos. Efectos secundarios (acumuladores de Ganancias) al confirmar, no al calcular (T2).
- **Nada de importes legales escritos en el código o en las reglas**: alícuotas, topes, cuotas y escalas
  en la compañía o en tablas con vigencia. Las constantes que quedan (30 días, 1,5 / 2 de extras) van
  nombradas y con su norma.
- **Fallar con un mensaje claro, nunca inventar datos.** Prohibidos los valores de relleno (CUIL
  20000000000, CBU con ceros, CUIT de ejemplo, "Córdoba", "Operario"): validar y listar lo que falta
  (E3, E4).
- **Nunca decidir por nombres o textos**: registros del módulo por xmlid, tipos de licencia y convenios por
  campo o marca, no por "vacaci" o "UOM" en el nombre.
- **Clasificar conceptos por atributos de la regla** (tipo de concepto, base de Obra Social / sindicato,
  gravado en Ganancias), no por listas de códigos sueltas en Python.
- Métodos cortos con un propósito; nombres en el idioma del código que rodea. Sin `sudo()` salvo necesidad
  justificada en el docstring.
- **Documentación Doxygen obligatoria** (`docs/recetas.md#documentar-código`): `@file`, docstring con qué y
  por qué (regla de negocio y norma), `@param`, `@return`, `@throws`, `@bug <id>` mientras exista el
  problema. `tests/test_documentacion.py` falla si falta algo o si `docs/referencia.md` quedó viejo.
- Docs y docstrings en español; commits y PR en inglés (como el historial).
- Cambio de comportamiento visible para el liquidador = actualizar la guía de usuario y su escenario.
