# Recetas

Cambios habituales, paso a paso. Al terminar cualquier cambio de código: tests, regenerar la
[referencia](referencia.md) (comando en [Operación](operacion.md#comandos-frecuentes)), actualizar el
documento de `docs/` que corresponda y commitear todo junto.

## Cambios que no requieren programar

| Quiero… | Dónde |
|---|---|
| Actualizar el tope imponible, una alícuota, la ART o un seguro | Compañía, pestaña *Nómina Argentina*. |
| Cambiar los coeficientes de contribución de un lote | El lote, *Parámetros de Liquidación AFIP / ARCA*. |
| Nueva escala salarial del convenio | *Categorías Laborales*: cargar el básico y *Actualizar Sueldos de Contratos*. |
| Nueva escala de Ganancias | *Ganancias: Escalas y Deducciones*: duplicar la anterior y cambiar fechas e importes. |
| Mismo valor de una novedad para todo el lote | Lote › *Novedades › Valores del Lote* › *Aplicar a todos*. |
| Feriados del año | Calendario › ausencias globales (sin recurso). |
| Corregir la retención de Ganancias de un recibo | Recibo › *Override Retención Ganancias*. |
| Base de contribuciones distinta para un jornalizado | Recibo › *Bruto Mes Anterior Manual*. |
| Antigüedad reconocida distinta | Recibo › *Override Antigüedad*. |

## Agregar un concepto con importe (premio, adicional, descuento)

1. En `data/salary_structure_jornal_data.xml`:
   - una regla (`hr.salary.rule`) con código, secuencia, categoría (`cat_rem`, `cat_norem`, `cat_ret`)
     y **tipo de concepto** (1, 2 o 3);
   - el **código LSD** registrado en ARCA (`afip_code`, nunca "0") y la unidad;
   - condición `inp('CÓDIGO') > 0` e importe `result = inp('CÓDIGO')` (negativo si es descuento);
   - un comentario `#` con qué es y su norma.
2. Una entrada (`hr.rule.input`) con el mismo código y `input_id` a la regla.
3. Agregar la regla a las estructuras que correspondan (`rule_ids`).
4. **Secuencia.** Los haberes van antes de 100 (`GROSS`); las retenciones entre 110 y 199. Si la
   antigüedad (20) tiene que incluirlo, va antes de 20. Si Ganancias (150) lo tiene que deducir, va
   antes de 150.
5. Si es una cantidad (horas, días, unidades), sumarla a `QUANTITY_INPUT_CODES` en
   `models/hr_payslip_run.py`, para que aparezca en la primera matriz.
6. Test en `tests/test_novedades.py`.
7. Actualizar la tabla de [Liquidación](liquidacion.md) y regenerar la referencia.

## Agregar una novedad automática

1. Calcularla en `hr.payslip._get_period_input_amounts()` (o en un módulo que lo extienda, como
   `payroll_arg_attendance`) y devolverla en el diccionario `{código: valor}`.
2. Se carga sola al crear el recibo y con *Recargar*. Un valor del lote tiene precedencia.
3. Documentarla en [Flujos](flujos.md#novedades).

## Agregar un parámetro para las reglas

1. Campo en `res.company` (y en el lote si se cambia por lote) con su vista.
2. Agregarlo a `hr.payslip.get_payroll_dict()`. Las reglas lo leen como `payroll.<clave>`.
3. Si es obligatorio, la regla hace `raise ValueError("Falta configurar …")`: el motor lo muestra con el
   nombre de la regla.
4. Documentarlo en [Operación](operacion.md#parámetros-de-la-compañía).

## Cambiar una fórmula

1. Editar la regla en el XML, con un comentario de qué cambió y por qué.
2. Correr `tests/test_recibos_referencia.py`. Si falla, el cambio rompe un recibo de referencia: confirmarlo con el
   liquidador antes de tocar el test.
3. Si cierra un punto de la [revisión](revision.md), quitar la marca `@bug` del código y el punto del
   documento.

## Escribir un test

Ver [Tests](tests.md): anatomía, ORM, `Form`, permisos y cómo correrlos.

## Documentar código

El código se documenta en formato **Doxygen**, en español (mismo criterio que `cotizador` y
`posventa`). `tests/test_documentacion.py` falla si falta algo; `tools/documentacion.py` dice
exactamente qué.

- **Archivo:** empieza con un docstring `@file` que dice qué contiene.
- **Clase y función:** docstring con **qué hace y por qué**, la regla de negocio y la norma (artículo de
  la LCT, ley, CCT). Las unidades de los importes (pesos, horas, días).
- **Primera oración:** es el resumen que Doxygen muestra en las listas, y la corta en el primer punto
  seguido de espacio. Escribirla sin abreviaturas con punto ("artículo 9 de la Ley 24.241", no
  "Art. 9"; "por ejemplo", no "p. ej."). Desde la segunda oración se puede abreviar.
- **Parámetros:** `@param` por cada uno; `@return` si devuelve algo; `@throws` para los errores que ve el
  usuario.
- **Problemas conocidos:** `@bug <id>` con el id de [revisión](revision.md). Doxygen arma la lista de bugs.
- **Constantes de módulo:** comentario `##` arriba.
- **Reglas salariales** (XML): comentario `#` al principio del código Python con el concepto, la norma
  y los ids de la revisión que la afectan.

```python
## Tipos de lote quincenales: usan medio tope imponible y la base de contribuciones del mes anterior.
QUINCENA_TYPES = ("1° Quincena", "2° Quincena", "Quincenal")


def _get_tope_imponible(self):
    """Tope imponible (base máxima, artículo 9 de la Ley 24.241) de los aportes del trabajador en este recibo.

    @return Importe en pesos (0 = sin tope).

    @bug C9 (docs/revision.md): un lote de SAC usa el tope mensual completo.
    """
```

## Actualizar la documentación

| Cambió… | Actualizar |
|---|---|
| Un modelo, campo, permiso, regla, estructura o método público | Regenerar `docs/referencia.md`. |
| Una fórmula o un concepto | `docs/liquidacion.md`. |
| Un tipo de lote, una novedad automática o un paso del proceso | `docs/flujos.md`. |
| Un parámetro, un menú o un comando | `docs/operacion.md`. |
| Se resolvió o apareció un problema | `docs/revision.md` y la marca `@bug`. |
| Se respondió una pregunta | Pasarla de `docs/pendientes.md` a `docs/decisiones.md`. |
| Un importe de los escenarios o un paso que ve el usuario | Regenerar `docs/usuario/resultados.md` y actualizar `docs/usuario/escenarios.md` / `guia.md`. |
