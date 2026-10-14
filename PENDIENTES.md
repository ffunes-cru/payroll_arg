# Pendientes y dudas abiertas — payroll_arg

Estado al 14/10/2026, rama `refactor/novedades-inputs`
(commits `7a86509` refactor y `d8bf77e` fixes en `payroll_arg`; `d6660f5` y `982acbf` en `payroll_arg_attendance`).

Los dos recibos reales de referencia (1° y 2° Quincena, valor hora $6.675,34, 6 años de
antigüedad) se reproducen al centavo y quedaron como tests en `tests/test_recibos_reales.py`.

## Dudas de negocio (necesitan confirmación)

### 1. Base de contribuciones patronales: ¿incluye el No Remunerativo?
- Implementado: base = remunerativo del **último mes con recibos calculados** (todas las
  liquidaciones de ese mes), o el valor manual "Bruto Mes Anterior Manual".
- Los recibos reales confirman alícuotas, coeficientes (0,10 / 0,15) y detracción, pero no
  cómo se arma la base, porque falta el mes anterior.
- **Cómo verificar:** sumar el remunerativo de los recibos del mes anterior al de cada imagen
  y comparar con 2.251.856,26 (Q1) y 3.945.490,21 (Q2). Si sólo coincide sumando el No
  Remunerativo, agregar `total_no_remunerativo` en `_get_prev_month_gross`.
- **Falta saber:** a qué mes pertenece cada imagen (tienen bases distintas, así que no son del
  mismo mes).
- Sólo aplica a jornalizados; los mensualizados contribuyen sobre el remunerativo del recibo.
  Confirmar si los mensualizados también deberían usar el mes anterior.

### 2. Doble conteo del costo patronal en reportes
El cuadro "Costo Total Empleado" de cada quincena muestra el costo del último mes declarado.
Q1 y Q2 del mismo mes llevan las contribuciones completas, así que sumar
`total_contribuciones` / `costo_total_empleador` de los recibos de un mes lo cuenta dos veces.
Sirve para el recibo, no para un reporte de costos. Definir si hace falta un costo "real" del
período.

### 3. Antigüedad sobre horas extras
- Implementado: base = (horas normales + feriado + extras 50% × 1,5 + extras 100% × 2) ×
  valor hora. Premios y presentismo quedan afuera (confirmado con los recibos).
- Los recibos reales no tienen horas extras: falta confirmar si las extras (y con qué
  recargo) entran en la base.
- Antigüedad sobre vacaciones jornal: hoy no entra (la regla VACACIONES va después). Confirmar.

### 4. Tope imponible en quincenas
Cada quincena usa la mitad del tope mensual. Lo correcto sería que la Q2 tope el total del
mes (Q1 + Q2). Confirmar criterio antes de cambiarlo.

### 5. Aporte Adicional Seg. Social en mensualizados
Ahora se descuenta en 2° Quincena **y en liquidaciones Mensuales** (como dice GEMINI.md).
Antes sólo en 2° Quincena. Confirmar.

### 6. Seguro de Vida UOM a cargo del trabajador
Agregado como `RET_UOM_VIDA` (desde la Q2, convencionados UOM), con el campo de compañía
"Seguro de Vida UOM Trabajador". Confirmar:
- el código de concepto para el LSD (puse `820002`, hay que registrarlo en la tabla de conceptos);
- si en mensualizados también corresponde.

### 7. Detracción SIPA en liquidaciones especiales
SAC, vacaciones y final aplican la detracción completa de nuevo. La detracción es mensual:
habría que aplicarla una sola vez por mes.

### 8. Ganancias
- El bruto para Ganancias usa sólo el remunerativo; las sumas No Remunerativas también
  están gravadas.
- Antes no descontaba los aportes de ley (leía una categoría `RET` inexistente). Ahora sí
  (`DED`, incluye cuota sindical y seguro de vida UOM): **los importes de Ganancias van a
  cambiar** respecto de liquidaciones anteriores.

## Pendientes técnicos

- **F.931 `remuneracion_01..11`:** todas iguales al remunerativo total; hay que mapearlas
  según la especificación de AFIP (topes, detracción, bases diferenciales).
- **Valores inventados en exportaciones:** `_to_recibo_dict` y `_get_afip_info_f931` todavía
  completan con valores ficticios si falta el dato (CUIL "20000000000", ingreso "2020-01-01",
  domicilio, obra social "126205", zona "18", etc.). Deberían bloquear la exportación con un
  error claro.
- **Acumulador de Ganancias:** se escribe desde dentro de la regla salarial; recalcular o
  previsualizar deja registros. Mover la escritura a la confirmación del recibo.
- **Varias versiones de contrato en el período** (aumento a mitad de mes): se toma la primera.
- **Recibo PDF:** la línea de antigüedad muestra "6 / base"; el recibo real muestra
  "0,06 / 400,52 por hora". El importe es el mismo.
- **Matriz del lote:** probada sólo por tests de servidor; falta revisarla en el navegador
  (columnas, totales, lote con jornalizados y mensualizados mezclados).
- **Hardcodeados restantes:** fallbacks de 44 hs/semana, 8 hs/día y 4,333 semanas/mes en
  reglas SAC/vacaciones jornal.
- **`hours_per_week` vs `full_time_required_hours`:** corregido en el cálculo; revisar si
  algún otro módulo (reportes) usa `full_time_required_hours` como horas del calendario.

## Al actualizar una base existente

- Reiniciar el servidor antes de actualizar (el botón "Actualizar" no recarga Python).
- La migración `19.0.2.0.0` elimina las 15 asistencias por defecto de los dos calendarios
  del módulo (pasan de 16,8 a 8,8 hs/día).
- Se eliminan los campos de novedades del recibo y del lote; sus valores no se migran
  (datos de prueba).
