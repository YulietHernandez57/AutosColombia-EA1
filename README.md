# Autos Colombia — Iteración 2

Aplicación académica de un parqueadero por mensualidades. Autora: Yuliet Hernández.

## Ejecutar en Windows

Descomprime el proyecto y abre una terminal en la carpeta. Requiere Python y un navegador.

```powershell
py app.py
py datos_prueba.py
py cuentas.py
py web.py
```

- `app.py` prepara SQLite y agrega los cambios de EA2 a la base de EA1.
- `datos_prueba.py` carga tres vehículos ficticios. Es opcional en una base con datos.
- `cuentas.py` crea la cuenta administradora. Ingresa tu propio usuario, nombre y una contraseña de al menos ocho caracteres. Ejecuta este paso una vez por cuenta.
- Abre http://127.0.0.1:8000. Detén el servidor con Ctrl+C. En otros sistemas puedes usar `python3` en lugar de `py`.

## Roles y demostración

- Administrador y operario pueden consultar la ocupación, gestionar clientes y vehículos, registrar entradas y salidas, corregir celdas y consultar movimientos.
- El administrador puede crear, desactivar y reactivar cuentas de operarios, cambiar el estado de celdas libres y consultar la bitácora de celdas.
- Para probar como operario, crea una cuenta desde **Cuentas de operarios**, cierra sesión e ingresa con esa cuenta.
- Un cliente puede tener varios vehículos. El documento identifica al cliente y la placa identifica al vehículo.
- Un cliente o un vehículo inactivo impide nuevos ingresos. Una estancia activa se puede cerrar mediante el comprobante.
- Hay 80 celdas físicas, 10 para motos y 70 para automóviles y camionetas. La capacidad operativa excluye las celdas fuera de servicio.
- La mensualidad se valida al ingreso. La gestión de cobros y pagos está fuera del alcance de esta iteración.

| Placa de prueba | Tipo | Mensualidad al cargar datos en una base nueva |
| --- | --- | --- |
| ABC123 | Automóvil | Vigente |
| ABC12D | Moto | Vigente |
| XYZ789 | Camioneta | Vencida |

Los vehículos nuevos se registran sin mensualidad precargada. Usa los datos de demostración para probar entradas y salidas. Cargar nuevamente los datos de prueba conserva las mensualidades existentes.

El servidor está configurado para una demostración local. La base de datos y las cuentas creadas en tu equipo se mantienen fuera del repositorio.

## Guion breve para el video de entrega

1. **Presentación.** “Soy Yuliet Hernández. Presento la segunda iteración del sistema de información Autos Colombia. Esta versión agrega gestión del personal, clientes, vehículos y celdas al flujo de entradas y salidas”.
2. **Usuarios y vehículos.** Inicia sesión como administradora, muestra la lista de cuentas y registra un cliente ficticio con una placa nueva. “La placa identifica el vehículo y un cliente puede tener varios asociados. Las operaciones se vinculan al usuario de la sesión”.
3. **Celdas.** Pon E01 fuera de servicio con el motivo Mantenimiento. Muestra que la capacidad operativa pasa de 80 a 79. Habilítala con el motivo Reparación terminada y revisa la bitácora.
4. **Flujo de EA1.** Consulta ABC123, registra el ingreso, muestra el comprobante y úsalo para registrar la salida. Enseña cómo se libera la celda en Ocupación.
5. **Cierre.** “Las pruebas verificaron el acceso por rol, el rechazo de placas duplicadas y que las celdas fuera de servicio queden excluidas de la asignación. El prototipo conserva el historial y se ejecuta localmente con Python y SQLite”.
