import sqlite3
from pathlib import Path

CARPETA = Path(__file__).resolve().parent

with sqlite3.connect(CARPETA / "autos_colombia.db") as conexion:
    conexion.execute("PRAGMA foreign_keys = ON;")

    esquema = (CARPETA / "schema.sql").read_text(encoding="utf-8")
    conexion.executescript(esquema)

    for numero in range(1, 11):
        conexion.execute(
            "INSERT OR IGNORE INTO celda (codigo, tipo) VALUES (?, ?)",
            (f"M{numero:02d}", "Moto")
        )

    for numero in range(1, 71):
        conexion.execute(
            "INSERT OR IGNORE INTO celda (codigo, tipo) VALUES (?, ?)",
            (f"E{numero:02d}", "Vehiculo")
        )

    conexion.executemany(
        """
        INSERT OR IGNORE INTO operario (nombre, usuario)
        VALUES (?, ?)
        """,
        [
            ("Ana Pérez", "operario1"),
            ("Carlos López", "operario2"),
            ("Laura Gómez", "operario3")
        ]
    )

    total = conexion.execute(
        "SELECT COUNT(*) FROM celda"
    ).fetchone()[0]

print(f"Autos Colombia: {total} celdas registradas.")