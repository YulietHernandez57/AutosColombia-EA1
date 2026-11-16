import hashlib
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path

CARPETA = Path(__file__).resolve().parent


def conectar():
    conexion = sqlite3.connect(CARPETA / "autos_colombia.db", timeout=15)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def derivar_clave(clave, sal):
    return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, 600_000)


def crear_cuenta(usuario, nombre, clave, rol="Operario"):
    usuario = usuario.strip().lower()
    nombre = nombre.strip()
    if not usuario or not nombre or len(clave) < 8:
        raise ValueError("Ingresa usuario, nombre y una contraseña de 8 caracteres o más.")
    sal = secrets.token_bytes(16)
    resumen = derivar_clave(clave, sal)
    with closing(conectar()) as conexion, conexion:
        conexion.execute("BEGIN IMMEDIATE")
        operario = conexion.execute(
            "SELECT id_operario FROM operario WHERE usuario = ?", (usuario,)
        ).fetchone()
        if operario is None:
            id_operario = conexion.execute(
                "INSERT INTO operario (usuario, nombre) VALUES (?, ?)", (usuario, nombre)
            ).lastrowid
        else:
            id_operario = operario["id_operario"]
            if conexion.execute(
                "SELECT 1 FROM cuenta WHERE id_operario = ?", (id_operario,)
            ).fetchone():
                raise ValueError("El usuario ya tiene una cuenta.")
            conexion.execute(
                "UPDATE operario SET nombre = ? WHERE id_operario = ?", (nombre, id_operario)
            )
        conexion.execute(
            "INSERT INTO cuenta (id_operario, rol, sal, clave) VALUES (?, ?, ?, ?)",
            (id_operario, rol, sal, resumen)
        )


def buscar_cuenta(usuario):
    with closing(conectar()) as conexion:
        return conexion.execute(
            """
            SELECT o.usuario, o.nombre, c.rol, c.sal, c.clave
            FROM cuenta c JOIN operario o USING (id_operario)
            WHERE o.usuario = ? AND c.activa = 1
            """,
            (usuario,)
        ).fetchone()


def autenticar(usuario, clave):
    cuenta = buscar_cuenta(usuario.strip().lower())
    sal = cuenta["sal"] if cuenta else bytes(16)
    resumen = derivar_clave(clave, sal)
    if cuenta and secrets.compare_digest(cuenta["clave"], resumen):
        return cuenta["usuario"]
    raise ValueError("Usuario o contraseña incorrectos.")


def cambiar_acceso_operario(usuario, activa):
    with closing(conectar()) as conexion, conexion:
        resultado = conexion.execute(
            """
            UPDATE cuenta SET activa = ?
            WHERE rol = 'Operario' AND id_operario = (
                SELECT id_operario FROM operario WHERE usuario = ?
            )
            """,
            (activa, usuario.strip().lower())
        )
        if resultado.rowcount == 0:
            raise ValueError("La cuenta de operario indicada no existe.")


if __name__ == "__main__":
    from getpass import getpass

    try:
        usuario = input("Usuario administrador: ")
        nombre = input("Nombre del administrador: ")
        clave = getpass("Contraseña: ")
        if clave != getpass("Confirma la contraseña: "):
            raise ValueError("Las contraseñas deben coincidir.")
        crear_cuenta(usuario, nombre, clave, "Administrador")
        print("Cuenta de administrador creada.")
    except (ValueError, sqlite3.Error) as error:
        raise SystemExit(str(error))
