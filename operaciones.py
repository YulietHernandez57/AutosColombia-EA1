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
            """
            SELECT v.*, p.activo AS cliente_activo
            FROM vehiculo v JOIN persona p USING (id_persona) WHERE v.placa = ?
            """,
            (placa,)
        ).fetchone()

        if vehiculo is None:
            raise ValueError("El vehículo no está registrado.")

        if not vehiculo["activo"] or not vehiculo["cliente_activo"]:
            raise ValueError("El cliente o el vehículo está inactivo.")

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
            FROM disponibilidad_celda AS c
            WHERE c.tipo = ? AND c.habilitada = 1
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


def cambiar_estado_celda(codigo, habilitada, motivo, usuario):
    codigo = codigo.strip().upper()
    motivo = motivo.strip()
    if not motivo:
        raise ValueError("Debes indicar el motivo del cambio.")

    with sqlite3.connect(
        CARPETA / "autos_colombia.db", timeout=15
    ) as conexion:
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.execute("BEGIN IMMEDIATE")

        operario = conexion.execute(
            "SELECT id_operario FROM operario WHERE usuario = ?", (usuario,)
        ).fetchone()
        if operario is None:
            raise ValueError("El operario no está registrado.")

        celda = conexion.execute(
            "SELECT * FROM disponibilidad_celda WHERE codigo = ?", (codigo,)
        ).fetchone()
        if celda is None:
            raise ValueError("La celda no existe.")
        if celda["habilitada"] == habilitada:
            estado = "habilitada" if habilitada else "fuera de servicio"
            raise ValueError(f"La celda {codigo} ya está {estado}.")

        ocupada = conexion.execute(
            '''
            SELECT 1 FROM estancia
            WHERE id_celda = ? AND fecha_hora_salida IS NULL
            ''',
            (celda["id_celda"],)
        ).fetchone()
        if ocupada:
            raise ValueError("La celda está ocupada. Libérala antes de cambiar su estado.")

        conexion.execute(
            '''
            INSERT INTO estado_celda (
                id_celda, id_operario, habilitada, motivo, fecha_hora
            ) VALUES (?, ?, ?, ?, ?)
            ''',
            (
                celda["id_celda"], operario["id_operario"], habilitada, motivo,
                datetime.now().isoformat(timespec="seconds")
            )
        )


def registrar_cliente_vehiculo(documento, nombre, placa, tipo, marca, modelo, color):
    documento, nombre, placa, marca, modelo, color = (
        valor.strip() for valor in (documento, nombre, placa, marca, modelo, color)
    )
    placa = placa.upper()
    if not all((documento, nombre, placa, marca, modelo, color)):
        raise ValueError("Completa todos los datos del cliente y del vehículo.")
    if tipo not in ("Moto", "Automovil", "Camioneta"):
        raise ValueError("Selecciona un tipo de vehículo válido.")

    with sqlite3.connect(CARPETA / "autos_colombia.db", timeout=15) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.execute("BEGIN IMMEDIATE")
        if conexion.execute("SELECT 1 FROM vehiculo WHERE placa = ?", (placa,)).fetchone():
            raise ValueError("La placa ya está registrada.")
        cliente = conexion.execute(
            "SELECT id_persona, nombre, activo FROM persona WHERE documento = ?", (documento,)
        ).fetchone()
        if cliente is None:
            id_persona = conexion.execute(
                "INSERT INTO persona (documento, nombre) VALUES (?, ?)", (documento, nombre)
            ).lastrowid
        else:
            id_persona, nombre_registrado, activo = cliente
            if not activo:
                raise ValueError("Reactiva al cliente antes de asociar un vehículo.")
            if nombre_registrado.casefold() != nombre.casefold():
                raise ValueError("El documento corresponde a un cliente con otro nombre.")
        conexion.execute(
            """
            INSERT INTO vehiculo (placa, tipo, marca, modelo, color, id_persona)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (placa, tipo, marca, modelo, color, id_persona)
        )
    return placa


def guardar_cliente(documento, nombre, modo):
    documento = documento.strip()
    nombre = nombre.strip()
    if not documento:
        raise ValueError("Ingresa el documento del cliente.")

    with sqlite3.connect(CARPETA / "autos_colombia.db", timeout=15) as conexion:
        if modo == "registrar" and nombre:
            if conexion.execute(
                "SELECT 1 FROM persona WHERE documento = ?", (documento,)
            ).fetchone():
                raise ValueError("El documento ya está registrado.")
            conexion.execute(
                "INSERT INTO persona (documento, nombre) VALUES (?, ?)", (documento, nombre)
            )
            return
        if modo == "actualizar" and nombre:
            resultado = conexion.execute(
                "UPDATE persona SET nombre = ? WHERE documento = ?", (nombre, documento)
            )
        elif modo in ("activar", "desactivar"):
            resultado = conexion.execute(
                "UPDATE persona SET activo = ? WHERE documento = ?",
                (modo == "activar", documento)
            )
        else:
            raise ValueError("Completa el nombre o selecciona un cambio de estado.")
        if resultado.rowcount == 0:
            raise ValueError("El cliente no existe.")


def actualizar_vehiculo(placa, marca, modelo, color, modo):
    placa = placa.strip().upper()
    marca, modelo, color = (valor.strip() for valor in (marca, modelo, color))
    with sqlite3.connect(CARPETA / "autos_colombia.db", timeout=15) as conexion:
        if modo in ("activar", "desactivar"):
            resultado = conexion.execute(
                "UPDATE vehiculo SET activo = ? WHERE placa = ?", (modo == "activar", placa)
            )
        elif modo == "actualizar" and all((marca, modelo, color)):
            resultado = conexion.execute(
                "UPDATE vehiculo SET marca = ?, modelo = ?, color = ? WHERE placa = ?",
                (marca, modelo, color, placa)
            )
        else:
            raise ValueError("Completa marca, modelo y color o selecciona un cambio de estado.")
        if resultado.rowcount == 0:
            raise ValueError("El vehículo no existe.")
