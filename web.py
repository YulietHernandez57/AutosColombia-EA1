import html
import secrets
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from operaciones import registrar_entrada, registrar_salida

CARPETA = Path(__file__).resolve().parent
TOKEN = secrets.token_hex(24)


def conectar():
    conexion = sqlite3.connect(
        CARPETA / "autos_colombia.db", timeout=15
    )
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def escapar(valor):
    return html.escape(str(valor if valor is not None else "—"))


def tabla(encabezados, filas):
    cabecera = "".join(
        f"<th>{escapar(campo)}</th>" for campo in encabezados
    )
    cuerpo = "".join(
        "<tr>"
        + "".join(f"<td>{escapar(valor)}</td>" for valor in fila)
        + "</tr>"
        for fila in filas
    )
    if not cuerpo:
        cuerpo = (
            f'<tr><td colspan="{len(encabezados)}">'
            "No hay registros.</td></tr>"
        )
    return (
        '<div class="tabla"><table><thead><tr>'
        + cabecera
        + "</tr></thead><tbody>"
        + cuerpo
        + "</tbody></table></div>"
    )


def campo(nombre, etiqueta, obligatorio=True):
    requerido = "required" if obligatorio else ""
    return (
        f"<label>{etiqueta}"
        f'<input name="{nombre}" {requerido} maxlength="250">'
        "</label>"
    )


def formulario(accion, contenido, boton):
    with conectar() as conexion:
        operarios = conexion.execute(
            "SELECT usuario, nombre FROM operario ORDER BY usuario"
        ).fetchall()

    opciones = "".join(
        f'<option value="{escapar(o["usuario"])}">'
        f'{escapar(o["nombre"])} ({escapar(o["usuario"])})'
        "</option>"
        for o in operarios
    )
    return (
        f'<form method="post" action="/{accion}">'
        f'<input type="hidden" name="token" value="{TOKEN}">'
        "<label>Operario"
        f'<select name="operario">{opciones}</select></label>'
        + contenido
        + f"<button>{boton}</button></form>"
    )


def corregir_celda(placa, codigo, motivo, usuario):
    placa = placa.strip().upper()
    codigo = codigo.strip().upper()
    motivo = motivo.strip()

    if not motivo:
        raise ValueError("Debes indicar el motivo del cambio.")

    with conectar() as conexion:
        conexion.execute("BEGIN IMMEDIATE")

        operario = conexion.execute(
            "SELECT id_operario FROM operario WHERE usuario = ?",
            (usuario,)
        ).fetchone()

        if not operario:
            raise ValueError("Operario no registrado.")

        estancia = conexion.execute(
            """
            SELECT e.*, v.tipo
            FROM estancia e
            JOIN vehiculo v ON v.id_vehiculo = e.id_vehiculo
            WHERE v.placa = ? AND e.fecha_hora_salida IS NULL
            """,
            (placa,)
        ).fetchone()

        if not estancia:
            raise ValueError("El vehículo no está dentro.")

        nueva = conexion.execute(
            "SELECT * FROM celda WHERE codigo = ?",
            (codigo,)
        ).fetchone()

        if not nueva:
            raise ValueError("La celda no existe.")

        if nueva["id_celda"] == estancia["id_celda"]:
            raise ValueError("El vehículo ya tiene esa celda.")

        compatible = (
            "Moto" if estancia["tipo"] == "Moto" else "Vehiculo"
        )
        if nueva["tipo"] != compatible:
            raise ValueError("La celda no es compatible con el vehículo.")

        ocupada = conexion.execute(
            """
            SELECT 1 FROM estancia
            WHERE id_celda = ? AND fecha_hora_salida IS NULL
            """,
            (nueva["id_celda"],)
        ).fetchone()

        if ocupada:
            raise ValueError("La celda de destino está ocupada.")

        conexion.execute(
            """
            INSERT INTO cambio_celda (
                fecha_hora, motivo, id_estancia, id_operario,
                id_celda_anterior, id_celda_nueva
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="microseconds"),
                motivo,
                estancia["id_estancia"],
                operario["id_operario"],
                estancia["id_celda"],
                nueva["id_celda"]
            )
        )

        conexion.execute(
            "UPDATE estancia SET id_celda = ? WHERE id_estancia = ?",
            (nueva["id_celda"], estancia["id_estancia"])
        )

    return f"Celda corregida: {placa} tiene asignada {codigo}."


def contenido_pagina(ruta):
    if ruta == "/entrada":
        return (
            "<h1>Registrar entrada</h1>"
            "<p>Consulta los datos y verifica visualmente el vehículo "
            "antes de confirmar su ingreso.</p>"
            '<form method="get" action="/consultar">'
            + campo("placa", "Placa")
            + "<button>Consultar vehículo</button></form>"
        )

    if ruta == "/salida":
        return (
            "<h1>Registrar salida</h1>"
            + formulario(
                "salida",
                campo("placa", "Placa")
                + campo("comprobante", "Código del comprobante"),
                "Confirmar salida"
            )
        )

    if ruta == "/corregir":
        return (
            "<h1>Corregir celda</h1>"
            + formulario(
                "corregir",
                campo("placa", "Placa")
                + campo("celda", "Nueva celda: M01–M10 o E01–E70")
                + campo("motivo", "Motivo del cambio"),
                "Guardar cambio"
            )
        )

    with conectar() as conexion:
        if ruta == "/historial":
            estancias = conexion.execute(
                """
                SELECT v.placa, c.codigo, e.fecha_hora_entrada,
                       e.fecha_hora_salida,
                       entrada.usuario AS operario_entrada,
                       salida.usuario AS operario_salida
                FROM estancia e
                JOIN vehiculo v ON v.id_vehiculo = e.id_vehiculo
                JOIN celda c ON c.id_celda = e.id_celda
                JOIN operario entrada
                    ON entrada.id_operario = e.id_operario_entrada
                LEFT JOIN operario salida
                    ON salida.id_operario = e.id_operario_salida
                ORDER BY e.id_estancia DESC
                """
            ).fetchall()

            cambios = conexion.execute(
                """
                SELECT v.placa, a.codigo, n.codigo,
                       cc.fecha_hora, cc.motivo, o.usuario
                FROM cambio_celda cc
                JOIN estancia e ON e.id_estancia = cc.id_estancia
                JOIN vehiculo v ON v.id_vehiculo = e.id_vehiculo
                JOIN celda a ON a.id_celda = cc.id_celda_anterior
                JOIN celda n ON n.id_celda = cc.id_celda_nueva
                JOIN operario o ON o.id_operario = cc.id_operario
                ORDER BY cc.id_cambio DESC
                """
            ).fetchall()

            return (
                "<h1>Historial</h1><h2>Entradas y salidas</h2>"
                "<p>La celda mostrada es la última asignada.</p>"
                + tabla(
                    [
                        "Placa", "Celda", "Entrada", "Salida",
                        "Operario entrada", "Operario salida"
                    ],
                    estancias
                )
                + "<h2>Cambios de celda</h2>"
                + tabla(
                    [
                        "Placa", "Anterior", "Nueva",
                        "Fecha", "Motivo", "Operario"
                    ],
                    cambios
                )
            )

        celdas = conexion.execute(
            """
            SELECT c.codigo, c.tipo,
                   CASE WHEN e.id_estancia IS NULL
                        THEN 'Disponible' ELSE 'Ocupada' END AS estado,
                   v.placa, e.fecha_hora_entrada
            FROM celda c
            LEFT JOIN estancia e
                ON e.id_celda = c.id_celda
                AND e.fecha_hora_salida IS NULL
            LEFT JOIN vehiculo v ON v.id_vehiculo = e.id_vehiculo
            ORDER BY c.tipo, c.codigo
            """
        ).fetchall()

        registrados = conexion.execute(
            "SELECT COUNT(*) FROM vehiculo"
        ).fetchone()[0]

    dentro = sum(c["estado"] == "Ocupada" for c in celdas)
    tarjetas = "".join(
        f'<div class="tarjeta">{titulo}<strong>{valor}</strong></div>'
        for titulo, valor in [
            ("Vehículos registrados", registrados),
            ("Vehículos dentro", dentro),
            ("Celdas disponibles", len(celdas) - dentro),
            ("Capacidad total", len(celdas))
        ]
    )

    resumen = ""
    for tipo, nombre in [
        ("Moto", "Motos"),
        ("Vehiculo", "Automóviles y camionetas")
    ]:
        grupo = [c for c in celdas if c["tipo"] == tipo]
        ocupadas = sum(c["estado"] == "Ocupada" for c in grupo)
        resumen += (
            f"<p><b>{nombre}:</b> {ocupadas} ocupadas y "
            f"{len(grupo) - ocupadas} disponibles de {len(grupo)}.</p>"
        )

    return (
        '<h1>Ocupación del parqueadero</h1>'
        '<a class="boton" href="/">Actualizar</a>'
        f'<div class="tarjetas">{tarjetas}</div>'
        + resumen
        + '<p><a class="boton" href="/entrada">Registrar entrada</a> '
        '<a class="boton" href="/salida">Registrar salida</a></p>'
        + tabla(
            ["Celda", "Tipo", "Estado", "Placa", "Hora de ingreso"],
            celdas
        )
    )


def consultar_vehiculo(placa):
    placa = placa.strip().upper()

    with conectar() as conexion:
        vehiculo = conexion.execute(
            """
            SELECT v.*, p.nombre AS persona
            FROM vehiculo v
            JOIN persona p ON p.id_persona = v.id_persona
            WHERE v.placa = ?
            """,
            (placa,)
        ).fetchone()

    if not vehiculo:
        raise ValueError("El vehículo no está registrado.")

    datos = tabla(
        ["Placa", "Tipo", "Marca", "Modelo", "Color", "Persona"],
        [[
            vehiculo["placa"], vehiculo["tipo"], vehiculo["marca"],
            vehiculo["modelo"], vehiculo["color"], vehiculo["persona"]
        ]]
    )
    return (
        "<h1>Verificar vehículo</h1>"
        + datos
        + "<p>Confirma que los datos coincidan con el vehículo presente. "
        "Al confirmar se validará la mensualidad y la disponibilidad.</p>"
        + formulario(
            "entrada",
            f'<input type="hidden" name="placa" value="{escapar(placa)}">',
            "Confirmar entrada y asignar celda"
        )
    )


def pagina(contenido):
    return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Autos Colombia</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0; background: #f2f5f9; color: #243247;
    font-family: Arial, sans-serif;
}
aside {
    position: fixed; width: 230px; height: 100vh;
    padding: 28px 20px; background: #163451; color: white;
}
aside h2 { margin-bottom: 35px; }
aside a {
    display: block; color: white; text-decoration: none;
    padding: 14px 10px; border-radius: 6px; margin-bottom: 7px;
}
aside a:hover { background: #2b5275; }
main { margin-left: 230px; padding: 35px; }
h1 { color: #163451; }
.tarjetas { display: flex; gap: 15px; flex-wrap: wrap; margin: 25px 0; }
.tarjeta {
    background: white; padding: 22px; border-radius: 10px;
    flex: 1; min-width: 170px; border: 1px solid #dfe6ed;
}
strong { display: block; font-size: 32px; margin-top: 12px; }
.tabla {
    overflow-x: auto; background: white;
    border-radius: 9px; margin: 20px 0;
}
table { width: 100%; border-collapse: collapse; }
th, td { padding: 13px; text-align: left; border-bottom: 1px solid #e5eaf0; }
th { background: #e6edf5; color: #163451; }
form {
    max-width: 600px; padding: 25px; background: white;
    border-radius: 10px; margin-top: 20px;
}
label { display: block; margin-bottom: 18px; font-weight: bold; }
input, select {
    width: 100%; padding: 12px; margin-top: 8px;
    border: 1px solid #bac8d5; border-radius: 6px; font-size: 16px;
}
button, .boton {
    display: inline-block; padding: 12px 18px; background: #163451;
    color: white; border: none; border-radius: 6px;
    cursor: pointer; text-decoration: none; font-size: 15px;
}
.aviso {
    background: white; border-left: 5px solid #247b65;
    padding: 22px; border-radius: 8px;
}
.error { border-left-color: #c44040; }
@media print {
    aside, button, .boton { display: none; }
    main { margin: 0; padding: 0; }
}
@media(max-width: 700px) {
    aside { position: static; width: 100%; height: auto; }
    main { margin-left: 0; padding: 18px; }
}
</style>
</head>
<body>
<aside>
<h2>Autos Colombia</h2>
<a href="/">Ocupación</a>
<a href="/entrada">Registrar entrada</a>
<a href="/salida">Registrar salida</a>
<a href="/corregir">Corregir celda</a>
<a href="/historial">Historial</a>
</aside>
<main>""" + contenido + "</main></body></html>"


class Servidor(BaseHTTPRequestHandler):
    def responder(self, contenido, estado=200):
        datos = pagina(contenido).encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/favicon.ico":
            self.send_error(404)
            return

        try:
            if url.path == "/consultar":
                parametros = parse_qs(url.query)
                placa = parametros.get("placa", [""])[0]
                contenido = consultar_vehiculo(placa)
            elif url.path in [
                "/", "/entrada", "/salida", "/corregir", "/historial"
            ]:
                contenido = contenido_pagina(url.path)
            else:
                self.responder("<h1>Página no encontrada</h1>", 404)
                return

            self.responder(contenido)
        except (ValueError, sqlite3.Error) as error:
            self.mostrar_error(error)

    def mostrar_error(self, error):
        self.responder(
            '<div class="aviso error"><h2>No se completó la operación</h2>'
            f"<p>{escapar(error)}</p></div>"
            '<p><a class="boton" href="/">Volver a ocupación</a></p>',
            400
        )

    def do_POST(self):
        try:
            longitud = int(self.headers.get("Content-Length", "0"))
            if longitud < 0 or longitud > 10000:
                raise ValueError("Solicitud demasiado grande.")

            datos = parse_qs(
                self.rfile.read(longitud).decode("utf-8")
            )

            def valor(nombre):
                return datos.get(nombre, [""])[0]

            if not secrets.compare_digest(valor("token"), TOKEN):
                raise ValueError("Recarga la página e intenta nuevamente.")

            ruta = urlparse(self.path).path

            if ruta == "/entrada":
                resultado = registrar_entrada(
                    valor("placa"), valor("operario")
                )
                contenido = (
                    "<h1>Comprobante de ingreso</h1>"
                    '<div class="aviso">'
                    + "".join(
                        f"<p><b>{etiqueta}:</b> "
                        f"{escapar(resultado[clave])}</p>"
                        for etiqueta, clave in [
                            ("Placa", "placa"),
                            ("Marca", "marca"),
                            ("Modelo", "modelo"),
                            ("Color", "color"),
                            ("Celda asignada", "celda"),
                            ("Fecha y hora", "fecha_entrada"),
                            ("Código del comprobante", "comprobante")
                        ]
                    )
                    + "</div><p>Conserva este comprobante para retirar "
                    "el vehículo.</p>"
                    '<button onclick="window.print()">Imprimir</button>'
                )

            elif ruta == "/salida":
                resultado = registrar_salida(
                    valor("placa"),
                    valor("comprobante"),
                    valor("operario")
                )
                contenido = (
                    "<h1>Salida registrada</h1>"
                    '<div class="aviso">'
                    f'<p>Placa: {escapar(resultado["placa"])}</p>'
                    f'<p>Celda liberada: '
                    f'{escapar(resultado["celda_liberada"])}</p>'
                    f'<p>Fecha: {escapar(resultado["fecha_salida"])}</p>'
                    "</div>"
                )

            elif ruta == "/corregir":
                mensaje = corregir_celda(
                    valor("placa"), valor("celda"),
                    valor("motivo"), valor("operario")
                )
                contenido = (
                    "<h1>Cambio registrado</h1>"
                    f'<div class="aviso">{escapar(mensaje)}</div>'
                )

            else:
                raise ValueError("Operación no válida.")

            contenido += (
                '<p><a class="boton" href="/">Volver a ocupación</a></p>'
            )
            self.responder(contenido)

        except (ValueError, sqlite3.Error) as error:
            self.mostrar_error(error)


if __name__ == "__main__":
    servidor = ThreadingHTTPServer(("127.0.0.1", 8000), Servidor)
    print("Autos Colombia está funcionando.")
    print("Abre en el navegador: http://127.0.0.1:8000")
    print("Para detener el servidor, presiona Ctrl + C.")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()