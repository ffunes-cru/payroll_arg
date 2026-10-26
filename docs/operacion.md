# Operación

## Puesta en marcha

1. **Instalar** `payroll_arg` y, si se usan fichadas, `payroll_arg_attendance`. Clonar con submódulos:
   `git clone --recurse-submodules` (sin `payroll_arg_reportes` el módulo no carga).
2. **Compañía** (*Ajustes › Compañías › pestaña Nómina Argentina (ARCA / AFIP)*): CUIT, tipo de empresa,
   alícuotas, coeficientes, tope, detracción, ART y seguros (ver abajo), y datos del último pago del
   F.931 (salen en el recibo, Art. 140 inc. j LCT; actualizarlos cada mes).
3. **Convenios y categorías** (*Nómina Argentina › Configuración*): cuota sindical y divisor de
   vacaciones del CCT; básicos de cada categoría (valor hora o sueldo). Con *Actualizar Sueldos de Contratos* se
   pasan a los contratos.
4. **Calendarios y feriados**: el módulo trae "Jornal Fábrica UOM (44 hs)" y "Administración / Mensual
   (40 hs)". Cargar los feriados del año como ausencias globales del calendario (sin recurso).
5. **Tipo de licencia de vacaciones**: usar *Licencia por Vacaciones (LCT)* para que se detecten.
6. **Ganancias**: cargar la escala vigente de ARCA (la de 2026 que trae el módulo es de ejemplo, ver C5)
   e importar los F.572.
7. **Usuarios**: el liquidador lleva *Haberes: Administrador*. RR. HH. y el resto, sin permisos de
   Haberes (ver [Seguridad](seguridad.md)). Con varias compañías, completar los parámetros y la escala
   de Ganancias en cada una.
8. **Empleados**: alta a mano o con *Importar / Exportar Empleados* (plantilla Excel). Cada contrato
   necesita tipo de salario, básico, estructura, calendario, CCT, categoría y códigos AFIP.

## Parámetros de la compañía

| Parámetro | Campo | Por defecto | Notas |
|---|---|---|---|
| Jubilación trabajador | `jubilacion_contrib_rate` | 11% | Ley 24.241 |
| INSSJP trabajador | `inssjp_contrib_rate` | 3% | Ley 19.032 |
| Obra Social trabajador | `os_worker_rate` | 3% | Ley 23.660 |
| Jubilación patronal | `jubilacion_patronal_rate` | 10,77% | Las cuatro suman 18% (Ley 27.541) |
| INSSJP patronal | `inssjp_patronal_rate` | 1,59% | |
| AAFF patronal | `aaff_patronal_rate` | 4,70% | |
| FNE patronal | `fne_patronal_rate` | 0,94% | |
| Obra Social patronal | `os_patronal_rate` | 6% | |
| Coef. contribuciones SS / OS | `coef_contrib_ss` / `coef_contrib_os` | 0,10 / 0,15 | Se copian a cada lote, donde se pueden cambiar. |
| Detracción | `detraccion_sipa` | 7.003,68 | Mensual. |
| Tope imponible | `tope_imponible_max_retencion` | 4.250.000 | **Actualizar cada mes** (movilidad). |
| ART variable | `art_variable_rate` | 5,82% | Según póliza. |
| ART cuota fija | `art_fixed_fee` | 1.300 | No se usa (C12). |
| SCVO | `life_insurance_fee` | 424,62 | Prima mensual. |
| Seguro de vida UOM (empleador / trabajador) | `uom_life_insurance_fee` / `uom_life_insurance_employee_fee` | 8.045,65 | Ver C18. |

Los parámetros no tienen fecha de vigencia: recalcular un recibo viejo usa los valores de hoy (T8).

## Importar novedades

*Lote › Importar Novedades (CSV)*. Separador `;` o `,`, UTF-8 o Latin-1, coma o punto decimal.

```csv
legajo,nombre,cuil,hs_norm,hs_ext50,hs_ext100,vac_dias,PRESENTISMO,CANT_VIANDAS
1001,Juan Carlos Perez,20301234563,88,10,4,0,394150.85,10
```

- El empleado se busca por `legajo`, después `cuil`, después `nombre`. Tiene que tener recibo
  editable en el lote.
- Las demás columnas son códigos de entrada (ver [referencia](referencia.md#novedades-entradas)). Se
  aceptan los encabezados históricos `hs_norm`, `horas_normales`, `vac_dias`, `vacaciones`, etc.
- Celda vacía = no se toca. Un código que no existe se guarda sin aviso (U1): revisar los encabezados.
- Ejemplo: `data/ejemplo_carga_masiva_horas.csv`.

## Comandos frecuentes

Desde la carpeta de Odoo (`~/odoo_sv/odoo`):

```bash
# Actualizar (reiniciar el servidor antes: el botón Actualizar no recarga Python)
.venv/bin/python odoo-bin -d <base> -u payroll_arg,payroll_arg_attendance --stop-after-init

# Tests de los dos módulos, en una base de prueba
.venv/bin/python odoo-bin -d <base_de_prueba> -u payroll_arg,payroll_arg_attendance \
    --test-tags /payroll_arg,/payroll_arg_attendance --stop-after-init --http-port=8092

# Regenerar docs/referencia.md (base con el módulo actualizado y sin reglas editadas a mano)
.venv/bin/python odoo-bin shell -d <base> --no-http <<< \
    "from odoo.addons.payroll_arg.tools.documentacion import escribir; escribir(env)"

# HTML de la documentación del código (desde addons/payroll_arg)
doxygen docs/Doxyfile   # → docs/api/html/index.html

# Sitio de documentación (el mismo que publica GitHub Pages), en http://127.0.0.1:8000
pip install -r requirements-docs.txt
mkdocs serve
mkdocs build --strict   # lo que corre el CI: falla con enlaces o anclas rotos
```

El sitio (<https://ffunes-cru.github.io/payroll_arg/>) lo publica `.github/workflows/docs.yml` en cada push a
`main` que toque `docs/`. Una página nueva de `docs/` tiene que agregarse al `nav` de `mkdocs.yml`.

`tests/test_documentacion.py` falla si falta un docstring o si `docs/referencia.md` quedó viejo.

## Actualizar una base existente

- Las reglas y estructuras (`salary_structure_jornal_data.xml`) se **reescriben** en cada actualización:
  un cambio hecho a mano en una regla desde la interfaz se pierde. Los cambios van en el XML.
- La escala de Ganancias y los datos de ejemplo son `noupdate`: no se pisan.
- 19.0.2.0.0 borra los campos de novedades del recibo y del lote (sus valores no se migran) y limpia las
  asistencias duplicadas de los calendarios.

## Problemas comunes

| Síntoma | Causa | Qué hacer |
|---|---|---|
| "Estos empleados no tienen contrato vigente entre…" (al generar) o "no tiene contrato vigente en el período" (al calcular) | Al empleado le falta la **fecha de inicio del contrato**, empieza después del período o su fecha de fin es anterior. | 1. *Empleados*, abrir el empleado. 2. Pestaña **Nómina**, arriba a la izquierda **Contrato**: cargar la fecha de inicio (la de ingreso); borrar la fecha de fin si no corresponde. 3. Guardar. 4. Volver al lote y **Generar nóminas** otra vez (o *Recalcular Recibos*). |
| "tiene salario básico $0" | Contrato sin básico. | Cargar el sueldo o el valor hora (o la categoría). |
| "Falta configurar la alícuota…" / "Coeficiente de contribución inválido" | Parámetro de la compañía o del lote en 0. | Completar en la compañía o en el lote. |
| La matriz no muestra un empleado o una columna | El recibo no tiene esa entrada. | *Recargar Novedades del Período* (agrega las que falten). |
| Horas o feriados de otro período | Se cambiaron las fechas del lote (T3). | *Recargar Novedades del Período*. |
| Vacaciones pagadas dos veces | Lote de Vacaciones + quincena / mes (C1). | Poner `VAC_DIAS` a pagar en 0 en el lote común. |
| Ganancias en 0 | No hay escala vigente para la fecha, o no alcanza. | *Ganancias: Escalas*; revisar el acumulador del empleado. |
| El recibo PDF o el LSD falla | Datos faltantes (CUIL, contrato) o recibo sin calcular. | El mensaje lista los empleados. |
| `ModuleNotFoundError: py_arg_reports` | Falta el submódulo. | `git submodule update --init` en `payroll_arg`. |
