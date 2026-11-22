import calendar
import json
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

CARPETA = Path(__file__).resolve().parent


def conectar():
    conexion = sqlite3.connect(CARPETA / "autos_colombia.db", timeout=15)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def hoy_local():
    return date.today()


def fin_de_mes_pagado(inicio):
    """Devuelve el último día incluido de un mes calendario."""
    anio = inicio.year + (inicio.month == 12)
    mes = inicio.month % 12 + 1
    dia = min(inicio.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia) - timedelta(days=1)


def validar_fecha(valor):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        raise ValueError("La fecha debe tener el formato AAAA-MM-DD.")
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ValueError("La fecha indicada no es válida.") from None


def a_centavos(valor):
    try:
        importe = Decimal(str(valor).strip())
    except InvalidOperation:
        raise ValueError("Ingresa un valor numérico válido.") from None
    if not importe.is_finite() or importe <= 0 or importe > Decimal("92233720368547758.07"):
        raise ValueError("La tarifa debe ser positiva y estar dentro del rango de almacenamiento.")
    if importe != importe.quantize(Decimal("0.01")):
        raise ValueError("La tarifa admite hasta dos decimales.")
    return int(importe * 100)


def usuario_activo(conexion, usuario, administrador=False):
    cuenta = conexion.execute(
        """
        SELECT o.id_operario, o.usuario, o.nombre, c.rol
        FROM operario o JOIN cuenta c USING (id_operario)
        WHERE o.usuario = ? AND c.activa = 1
        """,
        (usuario,)
    ).fetchone()
    if cuenta is None:
        raise ValueError("La cuenta del personal no está activa.")
    if administrador and cuenta["rol"] != "Administrador":
        raise ValueError("Solo el administrador puede modificar tarifas.")
    return cuenta


def tarifas_vigentes(conexion):
    return conexion.execute(
        """
        SELECT t.* FROM tarifa_mensual t
        WHERE t.id_tarifa = (
            SELECT MAX(ultima.id_tarifa) FROM tarifa_mensual ultima
            WHERE ultima.tipo_celda = t.tipo_celda
        )
        ORDER BY t.tipo_celda
        """
    ).fetchall()


def actualizar_tarifas(motos, vehiculos, usuario):
    valores = (("Moto", a_centavos(motos)), ("Vehiculo", a_centavos(vehiculos)))
    with closing(conectar()) as conexion, conexion:
        conexion.execute("BEGIN IMMEDIATE")
        cuenta = usuario_activo(conexion, usuario, administrador=True)
        conexion.executemany(
            """
            INSERT INTO tarifa_mensual (
                tipo_celda, valor_centavos, fecha_hora, id_operario
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (tipo, valor, datetime.now().isoformat(timespec="seconds"),
                 cuenta["id_operario"])
                for tipo, valor in valores
            ]
        )


def consultar_vehiculo(conexion, placa):
    vehiculo = conexion.execute(
        """
        SELECT v.*, p.nombre AS cliente, p.documento, p.activo AS cliente_activo
        FROM vehiculo v JOIN persona p USING (id_persona)
        WHERE v.placa = ?
        """,
        (placa.strip().upper(),)
    ).fetchone()
    if vehiculo is None:
        raise ValueError("La placa no está registrada.")
    return dict(vehiculo)


def siguiente_periodo(conexion, id_vehiculo, hoy):
    # Las fechas de vencimiento de EA1 y EA2 ya son inclusivas.
    inicio = hoy
    periodos = conexion.execute(
        """
        SELECT fecha_inicio, fecha_vencimiento FROM mensualidad
        WHERE id_vehiculo = ? AND fecha_vencimiento >= ?
        ORDER BY fecha_inicio, fecha_vencimiento
        """,
        (id_vehiculo, hoy.isoformat())
    ).fetchall()
    for periodo in periodos:
        desde = validar_fecha(periodo["fecha_inicio"])
        hasta = validar_fecha(periodo["fecha_vencimiento"])
        if desde > inicio:
            break
        if hasta >= inicio:
            inicio = hasta + timedelta(days=1)
    fin = fin_de_mes_pagado(inicio)
    solapamiento = conexion.execute(
        """
        SELECT 1 FROM mensualidad
        WHERE id_vehiculo = ? AND fecha_inicio <= ? AND fecha_vencimiento >= ?
        """,
        (id_vehiculo, fin.isoformat(), inicio.isoformat())
    ).fetchone()
    if solapamiento:
        raise ValueError("Existe un período futuro que se cruza con esta mensualidad.")
    return inicio, fin


def cotizar(conexion, placa):
    vehiculo = consultar_vehiculo(conexion, placa)
    if not vehiculo["activo"] or not vehiculo["cliente_activo"]:
        raise ValueError("Reactiva al cliente y al vehículo antes de registrar un pago.")
    tipo = "Moto" if vehiculo["tipo"] == "Moto" else "Vehiculo"
    tarifa = conexion.execute(
        """
        SELECT * FROM tarifa_mensual WHERE tipo_celda = ?
        ORDER BY id_tarifa DESC LIMIT 1
        """,
        (tipo,)
    ).fetchone()
    if tarifa is None:
        raise ValueError("El administrador debe configurar la tarifa.")
    hoy = hoy_local()
    inicio, fin = siguiente_periodo(conexion, vehiculo["id_vehiculo"], hoy)
    return {
        "id_vehiculo": vehiculo["id_vehiculo"],
        "placa": vehiculo["placa"],
        "cliente": vehiculo["cliente"],
        "documento": vehiculo["documento"],
        "tipo_vehiculo": vehiculo["tipo"],
        "id_tarifa": tarifa["id_tarifa"],
        "valor_centavos": tarifa["valor_centavos"],
        "fecha_pago": hoy.isoformat(),
        "fecha_inicio": inicio.isoformat(),
        "ultimo_dia": fin.isoformat(),
    }


def preparar_pago(placa, medio, referencia, usuario):
    medio = medio.strip()
    referencia = referencia.strip()
    if medio not in ("Efectivo", "Transferencia"):
        raise ValueError("Selecciona Efectivo o Transferencia.")
    if medio == "Transferencia" and not referencia:
        raise ValueError("Ingresa la referencia de la transferencia.")
    if len(referencia) > 250:
        raise ValueError("La referencia es demasiado larga.")
    if medio == "Efectivo":
        referencia = ""
    with closing(conectar()) as conexion, conexion:
        conexion.execute("BEGIN IMMEDIATE")
        cuenta = usuario_activo(conexion, usuario)
        datos = cotizar(conexion, placa)
        datos.update(medio=medio, referencia=referencia)
        codigo = secrets.token_urlsafe(32)
        conexion.execute(
            """
            INSERT INTO solicitud_pago (codigo, id_operario, fecha_hora, datos)
            VALUES (?, ?, ?, ?)
            """,
            (codigo, cuenta["id_operario"], datetime.now().isoformat(),
             json.dumps(datos, ensure_ascii=False))
        )
    return codigo, datos


def confirmar_pago(codigo, usuario):
    with closing(conectar()) as conexion, conexion:
        conexion.execute("BEGIN IMMEDIATE")
        cuenta = usuario_activo(conexion, usuario)
        solicitud = conexion.execute(
            "SELECT * FROM solicitud_pago WHERE codigo = ?", (codigo,)
        ).fetchone()
        if solicitud is None or solicitud["id_operario"] != cuenta["id_operario"]:
            raise ValueError("La solicitud de pago no corresponde a esta cuenta.")
        existente = conexion.execute(
            "SELECT codigo_comprobante FROM pago WHERE solicitud = ?", (codigo,)
        ).fetchone()
        if existente:
            return existente["codigo_comprobante"]
        edad = datetime.now() - datetime.fromisoformat(solicitud["fecha_hora"])
        if edad > timedelta(minutes=15):
            raise ValueError("El resumen venció. Consulta la placa y revisa el pago nuevamente.")
        datos = json.loads(solicitud["datos"])
        actual = cotizar(conexion, datos["placa"])
        if any(datos[campo] != valor for campo, valor in actual.items()):
            raise ValueError(
                "La tarifa, el cliente o la cobertura cambió. Revisa nuevamente el pago."
            )
        id_mensualidad = conexion.execute(
            """
            INSERT INTO mensualidad (fecha_inicio, fecha_vencimiento, id_vehiculo)
            VALUES (?, ?, ?)
            """,
            (datos["fecha_inicio"], datos["ultimo_dia"], datos["id_vehiculo"])
        ).lastrowid
        id_pago = conexion.execute(
            "SELECT COALESCE(MAX(id_pago), 0) + 1 FROM pago"
        ).fetchone()[0]
        comprobante = f"PAG-{id_pago:06d}"
        conexion.execute(
            """
            INSERT INTO pago (
                id_pago, codigo_comprobante, solicitud, id_mensualidad,
                id_vehiculo, id_operario, id_tarifa, valor_centavos,
                medio, referencia, fecha_hora, fecha_inicio, ultimo_dia,
                placa, cliente, documento, tipo_vehiculo, nombre_operario,
                usuario_operario
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_pago, comprobante, codigo, id_mensualidad,
                datos["id_vehiculo"], cuenta["id_operario"], datos["id_tarifa"],
                datos["valor_centavos"], datos["medio"], datos["referencia"],
                datetime.now().isoformat(timespec="seconds"),
                datos["fecha_inicio"], datos["ultimo_dia"], datos["placa"],
                datos["cliente"], datos["documento"], datos["tipo_vehiculo"],
                cuenta["nombre"], cuenta["usuario"]
            )
        )
    return comprobante


def obtener_pago(codigo):
    with closing(conectar()) as conexion:
        pago = conexion.execute(
            "SELECT * FROM pago WHERE codigo_comprobante = ?", (codigo,)
        ).fetchone()
    if pago is None:
        raise ValueError("El comprobante de pago no existe.")
    return dict(pago)


def historial_pagos(placa="", desde="", hasta=""):
    filtros = []
    valores = []
    if desde:
        validar_fecha(desde)
        filtros.append("date(fecha_hora) >= ?")
        valores.append(desde)
    if hasta:
        validar_fecha(hasta)
        filtros.append("date(fecha_hora) <= ?")
        valores.append(hasta)
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha inicial debe ser anterior o igual a la fecha final.")
    if placa.strip():
        filtros.append("placa = ?")
        valores.append(placa.strip().upper())
    consulta = "SELECT * FROM pago"
    if filtros:
        consulta += " WHERE " + " AND ".join(filtros)
    consulta += " ORDER BY id_pago DESC"
    with closing(conectar()) as conexion:
        return [dict(fila) for fila in conexion.execute(consulta, valores)]
