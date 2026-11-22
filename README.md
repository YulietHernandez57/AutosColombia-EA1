# Autos Colombia — Iteración 3

Aplicación académica de Yuliet Hernández para gestionar un parqueadero por mensualidades. Incluye las tres iteraciones del proyecto en una sola carpeta.

## Actualizar la carpeta que ya utilizas

1. Detén el servidor anterior con Ctrl+C.
2. Extrae el ZIP y copia sus archivos dentro de **Autos colombia 2 completo**, aceptando reemplazar los archivos de código.
3. Conserva el archivo **autos_colombia.db** de esa carpeta. Guarda las cuentas y los registros de tus pruebas.
4. Abre esa carpeta en VS Code y ejecuta en la terminal:

```powershell
py app.py
py web.py
```

Abre http://127.0.0.1:8000 e ingresa con tu cuenta existente. Si la página anterior está abierta, recárgala con Ctrl+F5.

El ZIP contiene archivos de código y esta guía. La base personal se genera y actualiza en tu equipo mediante app.py. Ese proceso crea las tablas de pagos y conserva los registros y vencimientos existentes.

## Instalación en un equipo sin base de datos

Requiere Python y un navegador. Utiliza la biblioteca estándar de Python y SQLite.

```powershell
py app.py
py datos_prueba.py
py cuentas.py
py web.py
```

Al ejecutar cuentas.py, escribe el nombre, el usuario y una contraseña de al menos ocho caracteres para la cuenta administradora. La contraseña queda oculta al escribirla. En sistemas que usan el comando python o python3, sustituye py por ese comando.

## Funciones de las tres iteraciones

- Consultar vehículos y validar mensualidades antes del ingreso.
- Asignar una celda habilitada, libre y compatible.
- Generar comprobantes de ingreso, registrar salidas y liberar celdas.
- Corregir la celda asignada y consultar movimientos.
- Iniciar y cerrar sesión como administrador u operario.
- Registrar clientes y vehículos, buscar clientes por nombre o documento y gestionar sus estados.
- Crear, editar, desactivar y reactivar cuentas de operarios como administrador.
- Cambiar el estado de celdas libres y consultar su bitácora como administrador.
- Configurar tarifas, registrar pagos, generar o renovar mensualidades.
- Consultar e imprimir comprobantes de pago y filtrar su historial por placa y fechas.

La capacidad física es de 80 celdas, con 10 para motos y 70 para automóviles y camionetas.

## Roles

| Función | Administrador | Operario |
| --- | --- | --- |
| Entradas, salidas, clientes y vehículos | Sí | Sí |
| Registro y consulta de pagos | Sí | Sí |
| Consulta e impresión de comprobantes | Sí | Sí |
| Tarifas y cuentas de operarios | Sí | Acceso restringido |
| Cambios de servicio y bitácora de celdas | Sí | Acceso restringido |

El servidor obtiene el usuario responsable de la sesión. El cambio de contraseña o la desactivación de una cuenta invalida sus sesiones.

## Reglas de pagos y mensualidades

- Las tarifas iniciales ficticias son **80.000 COP para motos** y **200.000 COP para automóviles y camionetas**. El administrador puede modificarlas en **Administrar tarifas**.
- Los pagos se registran por vehículo y cubren una mensualidad completa.
- Se aceptan Efectivo y Transferencia. La transferencia requiere una referencia y la confirmación del personal sobre el dinero recibido.
- Antes de guardar hay una pantalla de revisión con placa, valor, medio y fechas. Su vigencia es de 15 minutos. Si cambian los datos o la cobertura, se solicita revisar de nuevo.
- Un vehículo sin cobertura o con cobertura vencida recibe un período desde el día del pago.
- Una renovación anticipada comienza al terminar la cobertura consecutiva ya adquirida.
- La mensualidad corresponde a un mes calendario. Se toma la misma fecha del mes siguiente o su último día si ese día no existe. El último día cubierto es el día anterior a ese límite.
- Ejemplo de demostración: inicio 21/11/2026, último día cubierto 20/12/2026. Una renovación comienza el 21/12/2026.
- Caso de fin de mes: inicio 31/01/2026, último día cubierto 27/02/2026. El siguiente período comienza el 28/02/2026.
- La columna histórica fecha_vencimiento conserva el significado inclusivo de EA1 y EA2. En las pantallas se llama **Último día cubierto**. Las mensualidades anteriores conservan sus fechas.
- El pago y la mensualidad se guardan en una transacción. El reenvío de la misma confirmación devuelve el mismo comprobante.
- Los comprobantes conservan el nombre del cliente, placa, tarifa aplicada, cobertura y responsable de la operación.
- La salida se puede registrar aunque la mensualidad venza durante la estancia.
- Un vehículo dentro del parqueadero debe salir antes de ser desactivado.

Para el informe, describe fecha_vencimiento como el último día incluido. Esto alinea la documentación con la implementación y con las etiquetas del prototipo.

## Demostración paso a paso

1. Inicia sesión como administradora y abre **Administrar tarifas**.
2. Abre **Pagos y mensualidades**, consulta NEW123 y revisa sus datos.
3. Selecciona Transferencia, escribe una referencia ficticia y pulsa **Revisar pago**.
4. Comprueba el resumen y pulsa **Confirmar pago**.
5. Muestra el comprobante y prueba **Imprimir comprobante**.
6. Entra en **Historial de pagos**, filtra por NEW123 y abre el comprobante.
7. Ve a **Registrar entrada**, consulta NEW123 y confirma.
8. Copia el comprobante de ingreso y úsalo en **Registrar salida**.

NEW123 se crea sin cobertura al cargar datos_prueba.py en una base nueva. Si ya lo registraste en tu base, el script conserva ese registro. Las fechas de pago se calculan usando la fecha del equipo en que ejecutas la aplicación.

Los vehículos de prueba ABC123 y ABC12D reciben cobertura al cargar por primera vez sus datos. XYZ789 tiene cobertura vencida. Volver a ejecutar datos_prueba.py conserva las mensualidades existentes.

## Archivos

| Archivo | Función |
| --- | --- |
| app.py | Prepara y actualiza la base de datos. |
| schema.sql | Tablas, relaciones e índices de las tres iteraciones. |
| datos_prueba.py | Carga registros ficticios de demostración. |
| cuentas.py | Cuentas del personal y contraseñas. |
| operaciones.py | Entradas, salidas, clientes, vehículos y celdas. |
| pagos.py | Tarifas, cotizaciones, pagos y mensualidades. |
| vistas_pagos.py | Pantallas de tarifas, pagos, comprobantes e historial. |
| web.py | Servidor HTTP local, sesiones, permisos y pantallas. |

## Verificación

Se ejecutaron 20 pruebas automáticas en bases temporales para comprobar fechas, dinero, permisos, pagos duplicados y concurrentes, reversión ante fallos, historial, flujo HTTP, ingreso después del pago, salida, actualización de cuentas y conservación de datos de EA2. También se comprobó la compilación de los módulos.

La aplicación se ejecuta en la dirección local 127.0.0.1. Los registros de pagos son confirmaciones realizadas por el personal dentro del prototipo académico.

## Actualizar GitHub

Carga en el repositorio los archivos de código, schema.sql y README.md. La base autos_colombia.db y __pycache__ corresponden al uso local.
