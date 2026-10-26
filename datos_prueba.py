import sqlite3
from pathlib import Path
from datetime import date, timedelta

CARPETA = Path(__file__).resolve().parent
hoy = date.today()

with sqlite3.connect(CARPETA / "autos_colombia.db") as conexion:
    conexion.execute("PRAGMA foreign_keys = ON;")

    conexion.execute(
        """
        INSERT OR IGNORE INTO persona (documento, nombre)
        VALUES (?, ?)
        """,
        ("DEMO001", "Cliente de prueba")
    )

    persona = conexion.execute(
        "SELECT id_persona FROM persona WHERE documento = ?",
        ("DEMO001",)
    ).fetchone()[0]

    vehiculos = [
        ("ABC123", "Automovil", "Toyota", "Corolla", "Blanco"),
        ("XYZ789", "Camioneta", "Renault", "Duster", "Gris"),
        ("ABC12D", "Moto", "Yamaha", "FZ", "Negro")
    ]

    for placa, tipo, marca, modelo, color in vehiculos:
        conexion.execute(
            """
            INSERT OR IGNORE INTO vehiculo
            (placa, tipo, marca, modelo, color, id_persona)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (placa, tipo, marca, modelo, color, persona)
        )

        vehiculo = conexion.execute(
            "SELECT id_vehiculo FROM vehiculo WHERE placa = ?",
            (placa,)
        ).fetchone()[0]

        existe = conexion.execute(
            "SELECT 1 FROM mensualidad WHERE id_vehiculo = ?",
            (vehiculo,)
        ).fetchone()

        if not existe:
            # La camioneta tendrá una mensualidad vencida.
            if placa == "XYZ789":
                inicio = hoy - timedelta(days=40)
                vencimiento = hoy - timedelta(days=10)
            else:
                inicio = hoy
                vencimiento = hoy + timedelta(days=30)

            conexion.execute(
                """
                INSERT INTO mensualidad
                (fecha_inicio, fecha_vencimiento, id_vehiculo)
                VALUES (?, ?, ?)
                """,
                (inicio.isoformat(), vencimiento.isoformat(), vehiculo)
            )

print("Datos de prueba guardados.")
print("ABC123 y ABC12D: mensualidad vigente.")
print("XYZ789: mensualidad vencida.")