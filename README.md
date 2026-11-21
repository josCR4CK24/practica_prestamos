
# Préstamos de Equipos UNICAH

**Asignatura:** Programación de Negocios  
**Plataforma:** Odoo 20.0  
**Estudiante:** José Carlos Cáceres Girón  
**Número de cuenta:** 0703-2006-03787  

## Descripción del proyecto

En esta práctica desarrollé el módulo `prestamo_unicah` para administrar los préstamos de equipos de la universidad utilizando Odoo 20.0.

El sistema permite registrar equipos como laptops, proyectores y dispositivos de audio, gestionar préstamos a estudiantes y docentes, controlar las fechas de devolución y consultar el estado de los equipos.

El trabajo se realizó siguiendo los seis pasos de la guía proporcionada en clase. También se desarrollaron los cuatro retos adicionales.

## 1. Requisitos e instalación

Para desarrollar y probar el módulo utilicé:

- Windows 11.
- Odoo 20.0.
- Python y el entorno virtual de Odoo.
- PostgreSQL.
- Visual Studio Code.
- Git y GitHub.

**Módulo:** `prestamo_unicah`  
**Base de datos:** `practica_prestamos_db`  
**Dependencia:** `mail`

El módulo se encuentra dentro de la carpeta `prestamo_unicah` de este repositorio.

### Ejecución en PowerShell

Los siguientes comandos corresponden a la configuración utilizada en mi computadora. Las rutas deben adaptarse si se instala el proyecto en otro equipo.

```powershell
Set-Location C:/OdooFuente/odoo

$opciones = @(
    '-c', 'C:/OdooFuente/odoo/odoo_pg18.conf',
    '--addons-path=C:/OdooFuente/odoo/addons,C:/OdooFuente/practica_prestamos',
    '--data-dir=C:/OdooFuente/practica_prestamos/odoo-data',
    '-d', 'practica_prestamos_db',
    '--db-filter=^practica_prestamos_db$',
    '--http-interface=127.0.0.1',
    '--http-port=8078'
)
```

Para instalar el módulo por primera vez:

```powershell
& ./.venv/Scripts/python.exe -B odoo-bin @opciones -i prestamo_unicah --stop-after-init --no-http
```

Para actualizarlo después de realizar cambios:

```powershell
& ./.venv/Scripts/python.exe -B odoo-bin @opciones -u prestamo_unicah --stop-after-init --no-http
```

Para iniciar Odoo:

```powershell
& ./.venv/Scripts/python.exe -B odoo-bin @opciones
```

Una vez iniciado, se puede acceder desde:

http://127.0.0.1:8078/odoo?db=practica_prestamos_db

El acceso se realiza con el usuario administrador configurado en la base de datos de la práctica.
Usuario: admin | Contraseña: admin

## 2. Desarrollo de la práctica

### Paso 1. Catálogo de equipos

Se creó el modelo `prestamo.equipo` para registrar los equipos que pueden ser prestados.
Cada equipo tiene su nombre, código, categoría, estado y disponibilidad. También se configuraron los permisos y las vistas necesarias para administrar los registros.
Se agregaron cuatro equipos iniciales y posteriormente se creó un micrófono con el código `AUD-002` para comprobar el funcionamiento del formulario.

### Paso 2. Registro de préstamos

Se creó el modelo `prestamo.prestamo` para registrar las solicitudes de préstamo.
Cada registro permite indicar el solicitante, el tipo de solicitante, las fechas y el estado del préstamo.
También se incorporó el chatter de Odoo para guardar el historial de los cambios realizados.

### Paso 3. Equipos del préstamo

Se creó el modelo `prestamo.linea`, que permite relacionar varios equipos con un mismo préstamo.
Se configuraron las relaciones entre modelos y los campos calculados para mostrar la cantidad total de equipos y los días del préstamo.
Para comprobarlo, se creó el préstamo **Clase de Redes**, agregando dos laptops y estableciendo un período de tres días.

### Paso 4. Flujo de estados

Se implementaron los botones **Prestar** y **Devolver**.
Al prestar un equipo, su estado cambia a Prestado. Cuando se devuelve, vuelve a estar Disponible.
Los cambios también quedan registrados en el historial del préstamo.

### Paso 5. Reglas del préstamo

Se implementaron las validaciones solicitadas para evitar registros incorrectos:

- La fecha de devolución no puede ser anterior a la fecha del préstamo.
- Un estudiante no puede solicitar un préstamo por más de siete días.
- Un equipo no puede agregarse dos veces al mismo préstamo.
- Un estudiante no puede solicitar más de dos equipos.
- No se puede prestar un equipo que ya está prestado o se encuentra en mantenimiento.

También se comprobó el caso permitido de un docente que solicita tres equipos durante diez días.

### Paso 6. Contactos, kanban y búsqueda

Se agregó una sección en los contactos para consultar sus préstamos anteriores.
También se configuró la vista kanban de equipos, organizada por estados, y se incorporaron los filtros de préstamos activos y atrasados.
Finalmente, se agregaron las opciones para agrupar los préstamos por estado y por solicitante.

## 3. Respuestas a las preguntas de la guía

### Paso 1. Catálogo de equipos

**1. ¿Qué pasa cuando se desmarca Activo? ¿Por qué es mejor que borrar?**

El equipo queda archivado y deja de aparecer en las búsquedas normales. Es mejor que eliminarlo porque permite conservar la información y el historial de los préstamos anteriores.

**2. ¿Para qué sirve `copy=False` en `codigo`?**

Evita que se copie el mismo código al duplicar un equipo. De esta manera, el nuevo equipo debe recibir su propio código y no se repite el del registro original.

### Paso 2. Registro de préstamos

**1. ¿Qué hacen `_name` y `_inherit` en este modelo?**

`_name` define el nombre del modelo que estamos creando. En cambio, `_inherit` permite incorporar funciones de otro modelo, como el historial de mensajes de `mail.thread`.

**2. ¿Qué hace `tracking=True` en `state`?**

Permite que Odoo registre automáticamente los cambios de estado en el chatter del préstamo.

### Paso 3. Equipos del préstamo

**1. ¿Qué indica cada parámetro de `fields.One2many("prestamo.linea", "prestamo_id")`?**

`prestamo.linea` indica el modelo que contiene los equipos asociados al préstamo, mientras que `prestamo_id` es el campo que relaciona cada línea con su préstamo.

**2. ¿Qué pasa con las líneas al borrar un préstamo? ¿Dónde se define?**

Si se elimina un préstamo en borrador, también se eliminan sus líneas. Esto se configura mediante `ondelete="cascade"` en el campo `prestamo_id`.

### Paso 4. Flujo de estados

**1. ¿Por qué los métodos vuelven a validar el estado?**

Porque el estado puede cambiar antes de ejecutar una operación. Al comprobarlo nuevamente, evitamos prestar o devolver equipos cuando no corresponde.

**2. ¿Qué hace `prestamo.linea_ids.equipo_id.write(...)`? ¿Por qué no necesita un bucle?**

Permite actualizar los equipos relacionados con el préstamo. No necesita un bucle porque Odoo puede modificar varios registros al mismo tiempo utilizando `write()`.

### Paso 5. Reglas del préstamo

**1. ¿Por qué hace falta volver a comprobar disponibilidad?**

Porque un equipo puede cambiar de estado después de seleccionarlo. Por ejemplo, podría prestarse a otra persona o enviarse a mantenimiento. Por eso se comprueba nuevamente antes de confirmar el préstamo.

**2. ¿Cuándo se ejecutan `@api.constrains` y la validación de `action_prestar`?**

`@api.constrains` comprueba las restricciones cuando se crean o modifican los campos correspondientes. La validación de `action_prestar` se ejecuta cuando se utiliza la acción de prestar, antes de cambiar el estado de los equipos.

### Paso 6. Contacto, kanban y búsqueda

**1. ¿Qué pasa si se arrastra una tarjeta a otra columna? ¿Por qué?**

En una vista kanban normalmente se puede cambiar el estado de un registro al moverlo a otra columna. En esta práctica se deshabilitó esa opción para que los equipos pasen a Prestado únicamente mediante el proceso de préstamo.

**2. ¿Se crea una columna en la tabla de contactos para `prestamo_ids`?**

No. La relación se obtiene mediante el campo `partner_id`, que se encuentra en los registros de préstamos y permite identificar a qué contacto pertenece cada uno.

## 4. Retos adicionales

Después de completar los seis pasos principales, también se desarrollaron los cuatro retos de la guía.

**Reto 1. Marcar préstamos atrasados**

Se agregó la opción de marcar un préstamo como Atrasado cuando se supera la fecha de devolución. El cambio queda registrado en el historial y los equipos continúan prestados hasta que sean devueltos.

**Reto 2. Colores en la lista**

Se utilizaron colores para identificar más fácilmente los estados de los préstamos. Los atrasados aparecen en rojo y los devueltos en gris.

**Reto 3. Veces prestado**

Se agregó un contador que muestra cuántas veces aparece un equipo en los registros de préstamos, incluyendo los borradores.

**Reto 4. Mantenimiento**

Se incorporó la opción de enviar equipos disponibles a mantenimiento y devolverlos posteriormente al estado Disponible.
Mientras un equipo está prestado, el sistema impide cambiarlo directamente a mantenimiento.

## 5. Pruebas realizadas

Durante la práctica se comprobó el funcionamiento de los modelos, formularios, relaciones, botones, filtros y restricciones.

Entre las pruebas realizadas estuvieron:

- Crear y consultar equipos.
- Registrar préstamos con varios equipos.
- Calcular la cantidad de equipos y los días de préstamo.
- Prestar y devolver equipos.
- Comprobar los cambios de estado en el chatter.
- Intentar préstamos que incumplen las reglas.
- Consultar los préstamos desde los contactos.
- Utilizar la vista kanban y los filtros de búsqueda.
- Comprobar los cuatro retos adicionales.

También se ejecutaron pruebas automatizadas de Odoo.

**Resultado final reportado:** 11 pruebas ejecutadas, sin fallos ni errores.

Para ejecutar las pruebas:

```powershell
& ./.venv/Scripts/python.exe -B odoo-bin @opciones -u prestamo_unicah --test-tags=/prestamo_unicah --stop-after-init
```

## 6. Conclusión

Esta práctica me permitió comprender mejor cómo se crean módulos personalizados en Odoo y cómo se relacionan diferentes modelos para desarrollar una funcionalidad completa.

También pude trabajar con vistas, permisos, campos calculados, validaciones y cambios de estado.
El resultado es un módulo que permite llevar un control básico de los equipos universitarios y sus préstamos, aplicando las reglas establecidas en la guía.
El proyecto se encuentra publicado en GitHub, con los commits correspondientes a cada uno de los seis pasos y a los cuatro retos adicionales.
