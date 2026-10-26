# Decisiones de negocio confirmadas

Lo que ya se decidió y no se vuelve a discutir. Cada decisión dice de dónde salió. Si una norma parece
contradecir una decisión, se pregunta en [Preguntas abiertas](pendientes.md); no se cambia el código por
cuenta propia.

Cómo se agrega una decisión:
1. La pregunta se responde en `pendientes.md`.
2. Se pasa acá con fecha y origen.
3. Se borra de pendientes.
4. Se implementa en un PR que cita la decisión.

| # | Decisión | Origen | Afecta |
|---|---|---|---|
| D1 | **Quincena de jornalizados = 88 hs fijas** (2 × 44), con los feriados aparte. Si hay que descontar ausencias, ver P3. | Recibos de referencia | `_get_calendar_hours_for_period()` |
| D2 | **Tope imponible: medio tope por quincena**, cada quincena por separado ("es lo mismo, dejalo como está"; el liquidador comentó que se toma el tope "para 500 hs"). | Respuesta 15/10/2026 | `_get_tope_imponible()` |
| D3 | **Antigüedad (1% por año) sobre todo lo que se paga a valor hora**: normales, feriados y extras con su recargo ("se le calcula a todo como está"). Premios y presentismo afuera. | Respuesta 15/10/2026 y recibos de referencia | `ADIC_ANTIG` |
| D4 | **Sumas no remunerativas de convenio**: entran sólo en la base de aportes y contribuciones de **Obra Social** y del **sindicato**; no en jubilación ni en el resto de las contribuciones. | Respuesta 15/10/2026 | `RET_OS`, `RET_SIND`, `COMP_OS` (C8) |
| D5 | **Las sumas no remunerativas están gravadas en Ganancias** ("están gravados sí, hay que añadirlos"). | Respuesta 15/10/2026 | `RET_GANANCIAS` (C3) |
| D6 | **Ganancias = bruto − descuentos de ley del recibo − deducciones** (SIRADIG y personales). Que los importes cambien respecto de liquidaciones viejas es correcto. | Respuesta 15/10/2026 | `_calculate_ganancias_from_rules()` |
| D7 | **Contribuciones de jornalizados en quincena** sobre el remunerativo del último mes declarado: es el cuadro "Costo Total Empleado" de los recibos de referencia (alícuotas, coeficientes 0,10 / 0,15 y detracción confirmados con ellos). El doble conteo al sumar las dos quincenas es "error del ejemplo" (ver P10). | Recibos de referencia y respuesta 15/10/2026 | `_get_prev_month_gross()`, C20 |
| D8 | **Vacaciones de enero y febrero**: se liquidan en un recibo aparte cuando el empleado sale de vacaciones; puede caer en la 1° o en la 2° quincena. | Respuesta 15/10/2026 | C1, C11 |
| D9 | **Seguros de vida**: hay uno de UOM y otro "para todos que lo paga el empleador" (SCVO). Falta confirmar si existe además el UOM patronal (P6). | Respuesta 15/10/2026 | `RET_UOM_VIDA`, `COMP_SCVO`, `COMP_UOM_VIDA` |
| D10 | **Ajuste anual de Ganancias** del año anterior: el sistema tiene que soportarlo, con su exportación (alcance en P13). | Respuesta 15/10/2026 | C6 |
| D11 | **No hay datos de producción** todavía: los cambios de esquema no necesitan compatibilidad hacia atrás. | 26/10/2026 | Todo |
| D12 | **Revisión por PR temático con un commit por hallazgo**, merge con "Create a merge commit". | 26/10/2026 | Forma de trabajo (`CLAUDE.md`) |
