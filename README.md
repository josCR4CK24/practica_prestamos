# Préstamo de equipo UNICAH

**Programación de Negocios · Odoo 20.0**
**Estudiante:** José Carlos Cáceres Girón
**Cuenta:** 0703-2006-03787

El módulo `prestamo_unicah` registra el inventario de equipos de la universidad, los préstamos a estudiantes y docentes y la devolución de los equipos.

## Requisitos y ejecución

Windows 11, código fuente de Odoo 20.0, Python del entorno virtual de Odoo y PostgreSQL local. El módulo depende de `mail`. Se usa una base independiente, `practica_prestamos_db`.

En PowerShell, verifica primero que el nombre de la base esté libre antes de instalar por primera vez. La configuración local debe apuntar al servidor PostgreSQL correcto. Usa la carpeta que contiene el módulo en `--addons-path`.

```powershell
Set-Location C:/OdooFuente/odoo
$opciones = @(
    '-c', 'C:/OdooFuente/odoo/odoo_pg18.conf',
    '--addons-path=C:/OdooFuente/odoo/addons,C:/OdooFuente/practica_prestamos',
    '--data-dir=C:/OdooFuente/practica_prestamos/odoo-data',
    '-d', 'practica_prestamos_db',
    '--db-filter=^practica_prestamos_db$',
    '--http-interface=127.0.0.1', '--http-port=8078'
)
& ./.venv/Scripts/python.exe -B odoo-bin @opciones -i prestamo_unicah --stop-after-init --no-http
& ./.venv/Scripts/python.exe -B odoo-bin @opciones -u prestamo_unicah --stop-after-init --no-http
& ./.venv/Scripts/python.exe -B odoo-bin @opciones
```

Usa `-i` en la instalación inicial y `-u` para cargar cambios en una instalación existente. Abre [Odoo local](http://127.0.0.1:8078/odoo?db=practica_prestamos_db) e inicia sesión con un usuario interno.

## Verificación

1. En **Préstamos → Equipos**, revisa los cuatro equipos iniciales y crea el micrófono `AUD-002`. Cambia a lista para comparar los campos de cada equipo.
2. En **Préstamos → Préstamos**, crea **Clase de Redes** con un contacto, dos equipos y fechas separadas por tres días. Comprueba la cantidad, los días y la categoría de cada línea.
3. Pulsa **Prestar**, revisa los estados de los equipos y el chatter. Pulsa **Devolver** y confirma que los equipos vuelven a estar disponibles.
4. Prueba una devolución anterior a la entrega, un estudiante por diez días, un equipo duplicado, un estudiante con tres equipos e intenta prestar un borrador cuyo equipo pasó a mantenimiento. Luego presta tres equipos a un docente por diez días.
5. Revisa el historial del contacto, las columnas del kanban y los filtros y agrupaciones del menú de búsqueda. **Activos** incluye Prestado y Atrasado. **Atrasados** usa el estado Atrasado.
6. Ejecuta la suite de Odoo sobre la base de la práctica.

```powershell
& ./.venv/Scripts/python.exe -B odoo-bin @opciones -u prestamo_unicah --test-tags=/prestamo_unicah --stop-after-init
```

## Respuestas

### Paso 1 · Catálogo de equipos

1. **¿Qué pasa cuando se desmarca Activo? ¿Por qué es mejor que borrar?** El equipo queda archivado y sale de las búsquedas normales. Conserva su registro y las referencias de préstamos anteriores.
2. **¿Para qué sirve `copy=False` en `codigo`?** Al duplicar el equipo, Odoo omite el código original. Debe asignarse un código al nuevo equipo porque el campo es obligatorio.

### Paso 2 · Registro de préstamos

1. **¿Qué hacen `_name` y `_inherit` en este modelo?** `_name` registra el modelo nuevo `prestamo.prestamo`. `_inherit` incorpora las funciones de mensajería de `mail.thread`.
2. **¿Qué hace `tracking=True` en `state`?** Registra los cambios de estado en el chatter con el valor anterior y el nuevo.

### Paso 3 · Equipos del préstamo

1. **¿Qué indica cada parámetro de `fields.One2many("prestamo.linea", "prestamo_id")`?** El primero identifica el modelo de líneas. El segundo es el campo inverso que apunta al préstamo.
2. **¿Qué pasa con las líneas al borrar un préstamo? ¿Dónde se define?** Al borrar un borrador, PostgreSQL elimina sus líneas por `ondelete="cascade"` en `prestamo_id`. Los préstamos que ya salieron de borrador conservan su historial.

### Paso 4 · Flujo de estados

1. **¿Por qué los métodos vuelven a validar el estado?** Un método también puede invocarse por RPC, y otra transacción puede haber cambiado el estado desde que se abrió el formulario. La validación aplica al estado que el servidor procesa.
2. **¿Qué hace `prestamo.linea_ids.equipo_id.write(...)`? ¿Por qué no necesita un bucle?** La navegación por las relaciones produce un conjunto de equipos y `write` modifica todo el conjunto. El módulo usa ese mismo mecanismo en el método privado que actualiza el estado.

### Paso 5 · Reglas del préstamo

1. **¿Por qué hace falta volver a comprobar disponibilidad?** El dominio limita lo que ofrece el selector. Entre guardar y prestar, un equipo puede entrar en mantenimiento o quedar asignado a otro préstamo. Al prestar se bloquean los registros y se revisa que sigan disponibles.
2. **¿Cuándo se ejecutan `@api.constrains` y la validación de `action_prestar`?** Odoo invoca la restricción de fechas al crear o escribir con los campos declarados. La validación de cantidad y disponibilidad corre al invocar Prestar. La unicidad en PostgreSQL también protege las escrituras que llegan directamente al modelo de líneas.

### Paso 6 · Contacto, kanban y búsqueda

1. **¿Qué pasa si se arrastra una tarjeta a otra columna? ¿Por qué?** En un kanban agrupado y arrastrable, mover una tarjeta escribe el campo de agrupación. Aquí se deshabilitó el arrastre para que el estado Prestado se gestione con el flujo del préstamo.
2. **¿Se crea una columna en la tabla de contactos para `prestamo_ids`?** La relación se consulta a través de `partner_id`, la clave foránea que se almacena en la tabla de préstamos.

## Ajustes a la guía

- Se pasa `addons_path` desde la línea de comandos y se usa un directorio de datos dedicado a esta práctica.
- Se aplica la unicidad del equipo por préstamo en PostgreSQL. Así también se validan las ediciones directas de líneas.
- Los métodos bloquean los registros durante las transiciones. Las restricciones del servidor protegen estados y líneas incluso si se editan por RPC. El kanban se mantiene como vista de consulta por estado.
- Se conserva el formato `ir.access.csv` de la guía, que usa el código fuente instalado de Odoo 20.0.

## Resultados

La instalación inicial y la actualización de `prestamo_unicah` cargaron en Odoo 20.0 sobre `practica_prestamos_db`. La suite ejecutó ocho pruebas con cero fallos y cero errores. Validó los tres modelos, la creación de equipos con un usuario interno, la carga XML, relaciones y cálculos, el flujo y el chatter, cinco casos inválidos, el caso docente y la configuración de las vistas y búsquedas.

En el navegador se creó el micrófono `AUD-002` y se prestaron y devolvieron dos equipos en **Clase de Redes**. Se verificaron el chatter, el historial del contacto, el kanban con cinco equipos, los dos filtros y las dos agrupaciones.

## Retos

- **Marcar atrasado.** Un préstamo en Prestado se puede marcar Atrasado cuando ya pasó la fecha de devolución. El chatter conserva el cambio y los equipos permanecen prestados hasta que se devuelvan.
- **Colores en la lista.** Los préstamos atrasados se distinguen en rojo y los devueltos en gris.
- **Veces prestado.** El formulario y la tarjeta de cada equipo muestran cuántos préstamos lo incluyen, incluidos los borradores.
- **Mantenimiento.** El formulario permite enviar equipos disponibles a mantenimiento y devolverlos a Disponible. El servidor bloquea el cambio mientras el equipo esté prestado.

La suite final, con los cuatro retos cargados, ejecutó once pruebas con cero fallos y cero errores. Añadió comprobaciones para el vencimiento, el conteo de préstamos por equipo y la protección del estado durante mantenimiento.
