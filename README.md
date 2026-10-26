# Autos Colombia — Iteración 1

Aplicación académica para gestionar entradas y salidas de un
parqueadero que trabaja unicamente por mensualidades.

Autora: Yuliet Hernández.

## Funcionalidades

- Consultar vehículos registrados y sus características.
- Validar la vigencia de la mensualidad por vehículo.
- Registrar entradas y asignar una celda disponible y compatible.
- Generar e imprimir comprobantes de ingreso.
- Registrar salidas mediante placa y comprobante.
- Liberar la celda al registrar la salida.
- Corregir la celda asignada y guardar el motivo y el operario.
- Consultar ocupación, disponibilidad e historial.
- Impedir dos estancias abiertas para un vehículo o una celda.

Capacidad: 80 celdas, distribuidas en 10 para motos (M01–M10)
y 70 para automóviles y camionetas (E01–E70).

## Requisitos

- Python 3.14, versión utilizada durante las pruebas.
- Un navegador web.
- No requiere instalar paquetes externos: utiliza la biblioteca
  estándar de Python y SQLite.

## Ejecución en Windows

Descargar el repositorio, descomprimirlo y abrir una terminal
dentro de la carpeta del proyecto.

Ejecutar estos comandos en orden:

```powershell
py app.py
py datos_prueba.py
py web.py
```

Abrir en el navegador:

http://127.0.0.1:8000

Mantener la terminal abierta mientras se utiliza la aplicación.
Para detener el servidor, presionar Ctrl + C.

En sistemas sin el comando `py`, utilizar `python` o `python3`.

## Datos de demostración

Al crear una base de datos nueva y ejecutar datos_prueba.py:

| Placa | Vehículo | Mensualidad |
|---|---|---|
| ABC123 | Toyota Corolla blanco | Vigente |
| ABC12D | Moto Yamaha FZ negra | Vigente |
| XYZ789 | Renault Duster gris | Vencida |

Los datos son ficticios. Las mensualidades de demostración se
calculan respecto a la fecha de su primera carga. Ejecutar
nuevamente datos_prueba.py no renueva las mensualidades existentes.

Operarios disponibles: operario1, operario2 y operario3.

## Prueba desde la interfaz

1. Entrar en Registrar entrada y consultar ABC123.
2. Verificar sus características y confirmar el ingreso.
3. Conservar el código del comprobante generado.
4. Revisar la celda asignada en Ocupación.
5. Opcionalmente, corregirla a otra celda disponible.
6. Registrar la salida con ABC123 y su comprobante.
7. Revisar el historial y la liberación de la celda.

La asignación es aleatoria. Cada nuevo ingreso genera un
comprobante diferente.

## Archivos principales

- app.py: crea las tablas, las celdas y los operarios de prueba.
- schema.sql: estructura de la base de datos y restricciones.
- datos_prueba.py: carga vehículos y mensualidades ficticias.
- operaciones.py: registro de entradas y salidas.
- web.py: interfaz web, consultas y correcciones de celda.
- autos_colombia.db: base de datos local generada al ejecutar app.py.

## Alcance y decisiones de esta versión

La gestión completa de clientes y pagos corresponde a futuras
iteraciones. Esta entrega consulta datos previamente cargados.

El selector de operario es para demostración; no implementa
autenticación con contraseña.

Las fechas de mensualidad se guardan como AAAA-MM-DD y las
fechas de movimientos incluyen hora. En esta versión, la fecha
de vencimiento se considera incluida.

SQLite utiliza TEXT para almacenar fechas y horas. El SQL
implementado en schema.sql concreta esta adaptación del modelo.

Las entradas y correcciones usan transacciones de escritura.
Dos índices únicos parciales impiden estancias abiertas
duplicadas por vehículo o celda.

La aplicación se ejecuta localmente. No está configurada para
publicación en Internet.