import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

CARPETA = Path(__file__).resolve().parent


def registrar_entrada(placa, usuario_operario):
    placa = placa.strip().upper()

    with sqlite3.connect(
        CARPETA / "autos_colombia.db", timeout=15
    ) as conexion:
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON;")
        conexion.execute("BEGIN IMMEDIATE;")

        operario = conexion.execute(
            "SELECT id_operario FROM operario WHERE usuario = ?",
            (usuario_operario,)
        ).fetchone()

        if operario is None:
            raise ValueError("El operario no está registrado.")

        vehiculo = conexion.execute(
            "SELECT * FROM vehiculo WHERE placa = ?",
            (placa,)
        ).fetchone()

        if vehiculo is None:
            raise ValueError("El vehículo no está registrado.")

        abierta = conexion.execute(
            """
            SELECT 1
            FROM estancia
            WHERE id_vehiculo = ?
              AND fecha_hora_salida IS NULL
            """,
            (vehiculo["id_vehiculo"],)
        ).fetchone()

        if abierta:
            raise ValueError("El vehículo ya está dentro.")

        ahora = datetime.now()
        hoy = ahora.date().isoformat()

        mensualidad = conexion.execute(
            """
            SELECT 1
            FROM mensualidad
            WHERE id_vehiculo = ?
              AND fecha_inicio <= ?
              AND fecha_vencimiento >= ?
            """,
            (vehiculo["id_vehiculo"], hoy, hoy)
        ).fetchone()

        if mensualidad is None:
            raise ValueError(
                "El vehículo no tiene mensualidad vigente."
            )

        tipo_celda = (
            "Moto" if vehiculo["tipo"] == "Moto" else "Vehiculo"
        )

        celda = conexion.execute(
            """
            SELECT c.id_celda, c.codigo
            FROM celda AS c
            WHERE c.tipo = ?
              AND NOT EXISTS (
                  SELECT 1
                  FROM estancia AS e
                  WHERE e.id_celda = c.id_celda
                    AND e.fecha_hora_salida IS NULL
              )
            ORDER BY RANDOM()
            LIMIT 1
            """,
            (tipo_celda,)
        ).fetchone()

        if celda is None:
            raise ValueError(
                "No hay celdas disponibles para ese tipo."
            )

        comprobante = secrets.token_hex(12).upper()
        fecha_entrada = ahora.isoformat(timespec="microseconds")

        conexion.execute(
            """
            INSERT INTO estancia (
                fecha_hora_entrada,
                codigo_comprobante,
                id_vehiculo,
                id_celda,
                id_operario_entrada
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                fecha_entrada,
                comprobante,
                vehiculo["id_vehiculo"],
                celda["id_celda"],
                operario["id_operario"]
            )
        )

    return {
        "placa": placa,
        "marca": vehiculo["marca"],
        "modelo": vehiculo["modelo"],
        "color": vehiculo["color"],
        "celda": celda["codigo"],
        "fecha_entrada": fecha_entrada,
        "comprobante": comprobante
    }


def registrar_salida(placa, comprobante, usuario_operario):
    placa = placa.strip().upper()
    comprobante = comprobante.strip().upper()

    with sqlite3.connect(
        CARPETA / "autos_colombia.db", timeout=15
    ) as conexion:
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON;")
        conexion.execute("BEGIN IMMEDIATE;")

        operario = conexion.execute(
            "SELECT id_operario FROM operario WHERE usuario = ?",
            (usuario_operario,)
        ).fetchone()

        if operario is None:
            raise ValueError("El operario no está registrado.")

        estancia = conexion.execute(
            """
            SELECT e.*, c.codigo AS codigo_celda
            FROM estancia AS e
            JOIN vehiculo AS v
                ON v.id_vehiculo = e.id_vehiculo
            JOIN celda AS c
                ON c.id_celda = e.id_celda
            WHERE v.placa = ?
              AND e.fecha_hora_salida IS NULL
            """,
            (placa,)
        ).fetchone()

        if estancia is None:
            raise ValueError(
                "El vehículo no tiene una entrada abierta."
            )

        if not secrets.compare_digest(
            estancia["codigo_comprobante"], comprobante
        ):
            raise ValueError(
                "El comprobante no corresponde al vehículo."
            )

        fecha_salida = datetime.now().isoformat(
            timespec="microseconds"
        )

        conexion.execute(
            """
            UPDATE estancia
            SET fecha_hora_salida = ?,
                id_operario_salida = ?
            WHERE id_estancia = ?
            """,
            (
                fecha_salida,
                operario["id_operario"],
                estancia["id_estancia"]
            )
        )

    return {
        "placa": placa,
        "celda_liberada": estancia["codigo_celda"],
        "fecha_salida": fecha_salida
    }