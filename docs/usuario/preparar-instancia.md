# Preparar una instancia de prueba

Para el administrador. Deja una base de Odoo con los escenarios cargados para que un empleado haga los
ejercicios de [Escenarios](escenarios.md) sin tocar datos reales.

## 1. Base nueva

1. Crear una base **sin datos de demostración**, en español (Argentina), con la zona horaria
   `America/Argentina/Cordoba` en el usuario administrador.
2. Instalar `payroll_arg` y `payroll_arg_attendance` (instala también `payroll`, Ausencias y
   Asistencias):

   ```bash
   .venv/bin/python odoo-bin -d nomina_pruebas -i payroll_arg,payroll_arg_attendance --without-demo=all --stop-after-init
   ```

3. Compañía (*Ajustes › Compañías*): nombre, domicilio, CUIT y datos del último pago del F.931. Sin
   CUIT el recibo PDF y los archivos salen con datos de relleno (E4 en la
   [revisión](../revision.md#e4)).

## 2. Cargar los escenarios

```bash
.venv/bin/python odoo-bin shell -d nomina_pruebas --no-http <<< "from odoo.addons.payroll_arg.tools.escenarios import cargar; cargar(env); env.cr.commit()"
```

Carga y deja listo:

- **Parámetros de la compañía** con los que se calcularon los resultados esperados (alícuotas, tope
  4.250.000, detracción 7.003,68, coeficientes 0,10 / 0,15, ART 5,82%, seguros).
- **Zona horaria de Córdoba** en los dos calendarios del módulo.
- El **feriado** del 17/08/2026 en el calendario de jornalizados.
- Los **seis empleados** ficticios (legajos 9101 a 9106) con su contrato.
- Las **vacaciones aprobadas** de C (07 al 20/09) y de D (21 al 25/09).
- El **F.572** de E aplicado a su ficha.
- El **historial de Ganancias** de E de enero a julio.

Si se corre dos veces, avisa y no duplica.

## 3. Usuario del empleado que prueba

Crear un usuario interno con:

| Aplicación | Permiso |
|---|---|
| Haberes (Payroll) | **Administrador** (el oficial no puede usar lotes) |
| Empleados | Administrador (lo da Haberes) |
| Ausencias | Administrador (para aprobar licencias) |
| Asistencias | Administrador (si va a probar fichadas) |

Para comprobar los permisos de los demás perfiles (otra área, RR. HH.), ver [Seguridad](../seguridad.md).

## 4. Copia limpia para empezar de nuevo

Antes de entregarla, duplicar la base (*Gestor de bases de datos › Duplicar*) como
`nomina_pruebas_limpia`. Para que el empleado vuelva a empezar, borrar `nomina_pruebas` y duplicar la
limpia con ese nombre.

## 5. Ver la solución

Para comparar con lo que hizo el empleado, en **otra** base preparada igual:

```bash
.venv/bin/python odoo-bin shell -d nomina_solucion --no-http <<< "from odoo.addons.payroll_arg.tools.escenarios import cargar, ejecutar; cargar(env); ejecutar(env); env.cr.commit()"
```

Crea y calcula los ocho lotes de los ejercicios. Los importes son los de
[Resultados esperados](resultados.md).

## 6. Después de actualizar el módulo

Si un PR cambia cálculos, `docs/usuario/resultados.md` cambia en el mismo PR. Actualizar el módulo en la
instancia (`-u payroll_arg,payroll_arg_attendance`) y recalcular los lotes: deberían dar los importes
nuevos.
