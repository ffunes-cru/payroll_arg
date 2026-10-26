"""@file
Herramientas de documentación del módulo: verificación de docstrings y referencia generada.

1. **Docstrings** (faltantes()): todo módulo, clase y función de Python tiene docstring; cada parámetro
   tiene `@param` y cada función que devuelve un valor tiene `@return`. Es el formato que lee Doxygen
   (docs/Doxyfile). El test tests/test_documentacion.py falla si falta algo. `payroll_arg_attendance`
   usa las mismas funciones con su propia carpeta.

2. **Referencia** (generar() / escribir()): docs/referencia.md se arma con los metadatos del ORM
   (modelos, campos, permisos), las estructuras salariales y sus reglas (con el código Python de cada
   una) y los archivos del módulo (quién llama a cada método), así no se desactualiza. El mismo test
   falla si quedó vieja.

Regenerar la referencia (y commitear docs/referencia.md), en una base con el módulo instalado y sin
cambios manuales en las reglas:

    .venv/bin/python odoo-bin shell -d <base> --no-http <<< "from odoo.addons.payroll_arg.tools.documentacion import escribir; escribir(env)"
"""
import ast
import inspect
import re
from pathlib import Path

from lxml import etree

from odoo import models

## Nombre técnico del módulo.
MODULO = 'payroll_arg'
## Carpeta raíz del módulo.
RAIZ = Path(__file__).resolve().parent.parent
## Archivo de la referencia generada.
ARCHIVO = RAIZ / 'docs' / 'referencia.md'
## Carpetas con código Python propio ('' = sólo la raíz). Se excluyen tests/ (se documentan con su
## nombre) y el submódulo payroll_arg_reportes (librería externa con su propia documentación).
CARPETAS_PY = ('', 'models', 'wizard', 'tools', 'migrations')
## Prefijos de los modelos propios del módulo (los heredados se listan aparte).
PREFIJOS_MODELO = ('afip.', 'hr.ganancias.', 'hr.siradig.', 'hr.payslip.run.novelty', 'hr.payslip.run.input.import',
                   'payroll.arg.')
## Tipos de campo relacionales.
RELACIONALES = ('many2one', 'one2many', 'many2many')
## Nombres legibles del Tipo de Concepto AFIP de las reglas.
TIPOS_CONCEPTO = {'1': 'Rem.', '2': 'No rem.', '3': 'Retención', '4': 'Contrib. / total'}


# =============================================================================
#  1. Docstrings
# =============================================================================

def _archivos(carpetas, patron, raiz=RAIZ):
    """Archivos del módulo que coinciden con un patrón, en orden.

    @param carpetas Carpetas relativas a la raíz ('' = solo la raíz, sin subcarpetas).
    @param patron Patrón glob de los archivos, p. ej. '*.py'.
    @param raiz Carpeta raíz del módulo.
    @return Lista de Path.
    """
    archivos = []
    for carpeta in carpetas:
        base = raiz / carpeta
        archivos += sorted(base.glob(patron) if carpeta == '' else base.rglob(patron))
    return [a for a in archivos if '__pycache__' not in a.parts]


def _devuelve_valor(funcion):
    """Indica si una función de Python tiene algún `return <valor>` propio (sin contar funciones anidadas).

    @param funcion Nodo ast.FunctionDef.
    @return True si devuelve un valor distinto de None.
    """
    pendientes = list(funcion.body)
    while pendientes:
        nodo = pendientes.pop()
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        if isinstance(nodo, ast.Return) and nodo.value is not None and not (
                isinstance(nodo.value, ast.Constant) and nodo.value.value is None):
            return True
        pendientes.extend(ast.iter_child_nodes(nodo))
    return False


def _faltantes_funcion_py(funcion, donde):
    """Problemas de documentación de una función o método de Python.

    @param funcion Nodo ast.FunctionDef.
    @param donde Prefijo "archivo:línea" para los mensajes.
    @return Lista de mensajes.
    """
    doc = ast.get_docstring(funcion)
    if not doc:
        return [f"{donde}: {funcion.name}() sin docstring"]
    errores = []
    args = funcion.args
    nombres = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
    nombres += [a.arg for a in (args.vararg, args.kwarg) if a]
    for nombre in nombres:
        if nombre not in ('self', 'cls') and not re.search(rf'@param\s+{nombre}\b', doc):
            errores.append(f"{donde}: {funcion.name}() sin @param {nombre}")
    if _devuelve_valor(funcion) and '@return' not in doc:
        errores.append(f"{donde}: {funcion.name}() sin @return")
    return errores


def faltantes(raiz=RAIZ, carpetas=CARPETAS_PY):
    """Verifica la documentación de todo el Python de un módulo.

    @param raiz Carpeta raíz del módulo (por defecto payroll_arg).
    @param carpetas Carpetas a revisar, relativas a la raíz.
    @return Lista de mensajes "archivo:línea: problema"; vacía si está todo documentado.
    """
    errores = []
    for archivo in _archivos(carpetas, '*.py', raiz):
        relativo = archivo.relative_to(raiz)
        if archivo.name == '__manifest__.py':
            continue
        arbol = ast.parse(archivo.read_text(encoding='utf-8'))
        if not (ast.get_docstring(arbol) or '').startswith('@file'):
            errores.append(f"{relativo}:1: el módulo no empieza con un docstring '@file'")
        for nodo in ast.walk(arbol):
            donde = f"{relativo}:{getattr(nodo, 'lineno', 1)}"
            if isinstance(nodo, ast.ClassDef) and not ast.get_docstring(nodo):
                errores.append(f"{donde}: clase {nodo.name} sin docstring")
            elif isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                errores += _faltantes_funcion_py(nodo, donde)
    return errores


# =============================================================================
#  2. Referencia generada
# =============================================================================

def generar(env):
    """Arma el contenido de docs/referencia.md.

    @param env Entorno de Odoo con el módulo instalado.
    @return Texto Markdown.
    """
    propios = sorted((env[nombre] for nombre in env.registry if nombre.startswith(PREFIJOS_MODELO)),
                     key=lambda m: m._name)
    heredados = sorted(
        (env[nombre] for nombre in env.registry
         if not nombre.startswith(PREFIJOS_MODELO) and _campos_propios(env[nombre])),
        key=lambda m: m._name)
    secciones = [
        '# Referencia generada del módulo Nómina Argentina',
        '> Archivo generado por `tools/documentacion.py`: no editar a mano. '
        'Cómo regenerarlo: ver el encabezado de ese archivo.',
        '## Estructuras salariales',
        'Reglas de cada estructura en orden de cálculo (secuencia). Tipo = *Tipo de Concepto AFIP* '
        '(define en qué total cae la línea). Las fórmulas completas están en '
        '[Reglas salariales](#reglas-salariales); la explicación de negocio, en '
        '[Liquidación](liquidacion.md).',
        _estructuras(env),
        '## Novedades (entradas)',
        'Códigos que las reglas leen con `inp(\'CÓDIGO\')`. Cada recibo recibe una entrada por código de '
        'su estructura (ver [Flujos](flujos.md#novedades)).',
        _entradas(env),
        '## Reglas salariales',
        'Condición e importe de cada regla tal como se evalúan. Variables: `contract` (contrato), '
        '`employee`, `payslip` (el recibo), `categories.<CAT>` (suma de la categoría hasta esta regla), '
        '`inp(código)` (novedades) y `payroll.<clave>` (parámetros, ver `get_payroll_dict()`). '
        'Resultado: `result` × `result_qty` × `result_rate` / 100.',
        _reglas(env),
        '## Diagrama de datos',
        'Relaciones de los modelos propios (sin los asistentes). `}o--||` = muchos a uno obligatorio, '
        '`}o--o|` = muchos a uno opcional, `}o--o{` = muchos a muchos.',
        _diagrama([m for m in propios if not m._transient]),
        '## Modelos propios',
        *(_tabla_campos(m) for m in propios),
        '## Campos agregados a modelos de Odoo',
        *(_tabla_campos(m) for m in heredados),
        '## Puntos de entrada',
        'Métodos públicos (invocables por RPC) y quién los llama: botones de vistas, Python y reglas '
        'salariales. Las llamadas desde código se buscan por nombre, así que un nombre repetido en otro '
        'modelo puede aparecer de más.',
        _puntos_de_entrada(env, propios + heredados),
        '## Permisos por modelo',
        'L = leer, E = escribir, C = crear, B = borrar. Sin fila: el grupo no accede al modelo.',
        _matriz_acceso(env),
    ]
    return '\n\n'.join(secciones) + '\n'


def escribir(env):
    """Regenera docs/referencia.md.

    @param env Entorno de Odoo con el módulo instalado.
    @return Path del archivo escrito.
    """
    ARCHIVO.write_text(generar(env), encoding='utf-8')
    return ARCHIVO


def _celda(texto):
    """Texto apto para una celda de tabla Markdown (una línea, `|` escapado).

    @param texto Texto o valor cualquiera.
    @return Texto limpio.
    """
    return ' '.join(str(texto or '').split()).replace('|', '\\|')


def _registros_del_modulo(env, modelo):
    """Registros de un modelo creados por los datos XML del módulo.

    @param env Entorno de Odoo.
    @param modelo Nombre técnico del modelo.
    @return Recordset (sólo los que siguen existiendo).
    """
    datos = env['ir.model.data'].search([('module', '=', MODULO), ('model', '=', modelo)])
    return env[modelo].browse(datos.mapped('res_id')).exists()


def _estructuras(env):
    """Una tabla por estructura salarial del módulo con sus reglas en orden de cálculo.

    @param env Entorno de Odoo.
    @return Texto Markdown.
    """
    bloques = []
    for estructura in _registros_del_modulo(env, 'hr.payroll.structure').sorted('code'):
        filas = []
        for regla in estructura.rule_ids.sorted(lambda r: (r.sequence, r.code)):
            filas.append(
                f'| {regla.sequence} | `{regla.code}` | {_celda(regla.name)} | {_celda(regla.category_id.code)} '
                f'| {TIPOS_CONCEPTO.get(regla.tipo_concepto, "—")} | {_celda(regla.afip_code) or "—"} '
                f'| {_celda(regla.afip_unit) or "—"} |')
        bloques.append('\n'.join([
            f'### `{estructura.code}` — {_celda(estructura.name)}', '',
            '| Sec. | Código | Concepto | Categoría | Tipo | Cód. LSD | Unidad |',
            '|---|---|---|---|---|---|---|', *filas]))
    return '\n\n'.join(bloques)


def _entradas(env):
    """Tabla de los códigos de novedad y las reglas que los declaran.

    @param env Entorno de Odoo.
    @return Tabla Markdown.
    """
    por_codigo = {}
    for entrada in _registros_del_modulo(env, 'hr.rule.input'):
        nombre, reglas = por_codigo.setdefault(entrada.code, (entrada.name, set()))
        reglas.add(entrada.input_id.code)
    filas = [f'| `{codigo}` | {_celda(nombre)} | {", ".join(f"`{r}`" for r in sorted(reglas))} |'
             for codigo, (nombre, reglas) in sorted(por_codigo.items())]
    return '\n'.join(['| Código | Novedad | Declarada en |', '|---|---|---|', *filas])


def _reglas(env):
    """Condición y fórmula de cada regla salarial del módulo.

    @param env Entorno de Odoo.
    @return Texto Markdown.
    """
    bloques = []
    for regla in _registros_del_modulo(env, 'hr.salary.rule').sorted(lambda r: (r.sequence, r.code)):
        if regla.condition_select == 'python':
            condicion = f'```python\n{(regla.condition_python or "").strip()}\n```'
        else:
            condicion = 'Siempre.'
        if regla.amount_select == 'code':
            importe = f'```python\n{(regla.amount_python_compute or "").strip()}\n```'
        else:
            importe = _celda(regla.amount_select)
        bloques.append('\n\n'.join([
            f'### `{regla.code}` — {_celda(regla.name)}',
            f'Secuencia {regla.sequence} · categoría `{regla.category_id.code}` · '
            f'{TIPOS_CONCEPTO.get(regla.tipo_concepto, "sin tipo")} · LSD `{regla.afip_code or "—"}`',
            f'**Condición:**\n\n{condicion}', f'**Importe:**\n\n{importe}']))
    return '\n\n'.join(bloques)


def _campos_propios(modelo):
    """Campos que define o modifica este módulo en un modelo (sin columnas automáticas).

    @param modelo Modelo (recordset vacío).
    @return Lista de campos ordenada por nombre.
    """
    return [campo for nombre, campo in sorted(modelo._fields.items())
            if MODULO in campo._modules and nombre not in models.MAGIC_COLUMNS]


def _diagrama(modelos):
    """Diagrama entidad-relación Mermaid de los campos relacionales propios.

    @param modelos Modelos a incluir.
    @return Bloque Markdown con el diagrama.
    """
    def nodo(nombre):
        """Identificador Mermaid de un modelo: 'hr.payslip' → 'hr_payslip'.

        @param nombre Nombre técnico del modelo.
        @return Identificador.
        """
        return nombre.replace('.', '_')

    lineas = ['```mermaid', 'erDiagram']
    for modelo in modelos:
        for campo in _campos_propios(modelo):
            if campo.related or campo.type not in ('many2one', 'many2many'):
                continue
            if campo.type == 'many2one':
                relacion = '}o--||' if campo.required else '}o--o|'
            else:
                relacion = '}o--o{'
            lineas.append(f'    {nodo(modelo._name)} {relacion} {nodo(campo.comodel_name)} : {campo.name}')
    lineas.append('```')
    return '\n'.join(lineas)


def _detalle(campo):
    """Columna "Detalle" de un campo: destino, valores, obligatoriedad, cálculo y ayuda.

    @param campo Campo del ORM.
    @return Texto de la celda.
    """
    detalle = []
    if campo.type in RELACIONALES:
        detalle.append(f'→ `{campo.comodel_name}`')
    if campo.type == 'selection' and isinstance(campo.selection, list):
        detalle.append('valores: ' + ', '.join(f'`{clave}`' for clave, _etiqueta in campo.selection))
    if campo.required:
        detalle.append('obligatorio')
    if campo.related:
        ruta = campo.related if isinstance(campo.related, str) else '.'.join(campo.related)
        detalle.append(f"related `{ruta}`")
    elif campo.compute:
        detalle.append('calculado' + (' (guardado)' if campo.store else ''))
    if campo.help:
        detalle.append(campo.help)
    return _celda('; '.join(detalle))


def _tabla_campos(modelo):
    """Tabla de campos propios de un modelo.

    @param modelo Modelo (recordset vacío).
    @return Sección Markdown.
    """
    tipo = ' (asistente)' if modelo._transient else ' (abstracto)' if modelo._abstract else ''
    filas = [f'| `{c.name}` | {c.type} | {_celda(c.string)} | {_detalle(c)} |' for c in _campos_propios(modelo)]
    cabecera = f'### `{modelo._name}` — {_celda(modelo._description)}{tipo}'
    if not filas:
        return cabecera + '\n\nSin campos propios.'
    return '\n'.join([cabecera, '', '| Campo | Tipo | Etiqueta | Detalle |', '|---|---|---|---|', *filas])


def _metodos_publicos(modelo):
    """Métodos públicos que este módulo define en un modelo, con la primera línea de su docstring.

    @param modelo Modelo (recordset vacío).
    @return dict {nombre: resumen}.
    """
    metodos = {}
    for clase in type(modelo).__mro__:
        if not clase.__module__.startswith(f'odoo.addons.{MODULO}.'):
            continue
        for nombre, valor in vars(clase).items():
            if inspect.isfunction(valor) and not nombre.startswith('_') and not hasattr(models.BaseModel, nombre):
                metodos.setdefault(nombre, (inspect.getdoc(valor) or '').split('\n')[0])
    return metodos


def _llamadores(env):
    """Quién llama a cada método desde los botones de las vistas del módulo.

    @param env Entorno de Odoo.
    @return dict {(modelo, método): set de descripciones}.
    """
    llamadores = {}
    for vista in _registros_del_modulo(env, 'ir.ui.view'):
        for boton in etree.fromstring(vista.arch_db).iter('button'):
            if boton.get('type') == 'object':
                modelo = vista.model
                for ancestro in reversed(list(boton.iterancestors('field'))):
                    campo = env[modelo]._fields.get(ancestro.get('name'))
                    modelo = campo.comodel_name if campo is not None and campo.comodel_name else modelo
                llamadores.setdefault((modelo, boton.get('name')), set()).add(f'botón en `{vista.name}`')
    return llamadores


def _llamadas_codigo(metodo):
    """Archivos del módulo que llaman a un método por nombre: Python (fuera de tests/) y reglas
    salariales de los datos XML.

    @param metodo Nombre del método.
    @return set de descripciones de los archivos.
    """
    patron = re.compile(rf'\.{metodo}\(')
    archivos = _archivos(('models', 'wizard'), '*.py') + _archivos(('data',), '*.xml')
    return {f"{'reglas ' if archivo.suffix == '.xml' else ''}`{archivo.relative_to(RAIZ)}`" for archivo in archivos
            if patron.search(archivo.read_text(encoding='utf-8'))}


def _puntos_de_entrada(env, modelos):
    """Tabla de métodos públicos y sus llamadores.

    @param env Entorno de Odoo.
    @param modelos Modelos a incluir.
    @return Tabla Markdown.
    """
    llamadores = _llamadores(env)
    filas = []
    for modelo in modelos:
        for metodo, doc in sorted(_metodos_publicos(modelo).items()):
            origenes = sorted(llamadores.get((modelo._name, metodo), set()) | _llamadas_codigo(metodo))
            filas.append(f'| `{modelo._name}` | `{metodo}` | {_celda(doc)} | {_celda("; ".join(origenes)) or "—"} |')
    return '\n'.join(['| Modelo | Método | Qué hace | Llamado desde |', '|---|---|---|---|', *filas])


def _matriz_acceso(env):
    """Tabla de permisos de acceso (`ir.model.access`) del módulo.

    @param env Entorno de Odoo.
    @return Tabla Markdown.
    """
    filas = []
    for acceso in _registros_del_modulo(env, 'ir.model.access').sorted(
            lambda a: (a.model_id.model, a.group_id.name or '')):
        permisos = ''.join(letra if permitido else '-' for letra, permitido in (
            ('L', acceso.perm_read), ('E', acceso.perm_write), ('C', acceso.perm_create), ('B', acceso.perm_unlink)))
        filas.append(f'| `{acceso.model_id.model}` | {_celda(acceso.group_id.name or "Todos")} | `{permisos}` |')
    return '\n'.join(['| Modelo | Grupo | Permisos |', '|---|---|---|', *filas])
