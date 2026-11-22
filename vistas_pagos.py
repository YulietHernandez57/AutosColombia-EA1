import html
from contextlib import closing
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

import pagos


def escapar(valor):
    return html.escape(str(valor if valor is not None else "—"), quote=True)


def moneda(centavos):
    numero = f"{Decimal(centavos) / 100:,.2f}"
    return "$" + numero.translate(str.maketrans(",.", ".,")) + " COP"


def fecha(valor):
    return date.fromisoformat(valor[:10]).strftime("%d/%m/%Y")


def oculto(nombre, valor):
    return f'<input type="hidden" name="{nombre}" value="{escapar(valor)}">'


def formulario(accion, token, contenido, boton):
    return (
        f'<form method="post" action="/{accion}">'
        + oculto("token", token) + contenido
        + f'<button type="submit">{boton}</button></form>'
    )


def detalle(etiqueta, valor):
    return (
        '<div class="dato"><dt>' + escapar(etiqueta)
        + '</dt><dd>' + escapar(valor) + '</dd></div>'
    )


def pestanas(activa):
    return (
        '<nav class="pestanas">'
        f'<a class="{"seleccionada" if activa == "pago" else ""}" href="/pagos">Registrar pago</a>'
        f'<a class="{"seleccionada" if activa == "historial" else ""}" href="/pagos/historial">'
        'Historial de pagos</a></nav>'
    )


def pagina_tarifas(token, guardado=False):
    with closing(pagos.conectar()) as conexion:
        tarifas = {fila["tipo_celda"]: fila["valor_centavos"]
                   for fila in pagos.tarifas_vigentes(conexion)}
    valores = {
        tipo: str(Decimal(valor) / 100)
        for tipo, valor in tarifas.items()
    }
    aviso = '<p class="exito">Tarifas guardadas correctamente.</p>' if guardado else ""
    campos = (
        '<p>Los cambios se aplican a los nuevos pagos. Los comprobantes guardados conservan su valor.</p>'
        '<label>Mensualidad de motos — Valor en COP'
        f'<input type="number" min="0.01" step="0.01" name="motos" '
        f'value="{escapar(valores.get("Moto", ""))}" required '
        'oninvalid="this.setCustomValidity(\'Ingresa una tarifa mayor que cero, con máximo dos decimales.\')" '
        'oninput="this.setCustomValidity(\'\')"></label>'
        '<label>Mensualidad de automóviles y camionetas — Valor en COP'
        f'<input type="number" min="0.01" step="0.01" name="vehiculos" '
        f'value="{escapar(valores.get("Vehiculo", ""))}" required '
        'oninvalid="this.setCustomValidity(\'Ingresa una tarifa mayor que cero, con máximo dos decimales.\')" '
        'oninput="this.setCustomValidity(\'\')"></label>'
        '<p class="ayuda">Valores en pesos colombianos, mayores que cero. '
        'Las tarifas iniciales de 80.000 y 200.000 COP son ficticias para la demostración.</p>'
    )
    return (
        "<h1>Administrar tarifas</h1>" + aviso
        + formulario("tarifas", token, campos, "Guardar tarifas")
    )


def pagina_pagos(placa, token):
    contenido = (
        "<h1>Pagos y mensualidades</h1>" + pestanas("pago")
        + '<form class="busqueda" method="get" action="/pagos">'
        '<h2>Consultar vehículo</h2><label>Placa'
        f'<input name="placa" value="{escapar(placa)}" maxlength="250" required></label>'
        '<button>Consultar</button></form>'
    )
    if not placa.strip():
        return contenido
    with closing(pagos.conectar()) as conexion:
        vehiculo = pagos.consultar_vehiculo(conexion, placa)
        cobertura = conexion.execute(
            """
            SELECT fecha_inicio, fecha_vencimiento FROM mensualidad
            WHERE id_vehiculo = ? AND fecha_inicio <= ? AND fecha_vencimiento >= ?
            ORDER BY fecha_vencimiento DESC LIMIT 1
            """,
            (vehiculo["id_vehiculo"], pagos.hoy_local().isoformat(),
             pagos.hoy_local().isoformat())
        ).fetchone()
        cotizacion = None
        if vehiculo["activo"] and vehiculo["cliente_activo"]:
            cotizacion = pagos.cotizar(conexion, placa)
    estado = (
        f'Vigente hasta {fecha(cobertura["fecha_vencimiento"])}'
        if cobertura else "Sin cobertura vigente"
    )
    datos = "".join([
        detalle("Cliente", vehiculo["cliente"]),
        detalle("Documento", vehiculo["documento"]),
        detalle("Placa", vehiculo["placa"]),
        detalle("Tipo", vehiculo["tipo"]),
        detalle("Marca", vehiculo["marca"]),
        detalle("Modelo", vehiculo["modelo"]),
        detalle("Estado del cliente", "Activo" if vehiculo["cliente_activo"] else "Inactivo"),
        detalle("Estado del vehículo", "Activo" if vehiculo["activo"] else "Inactivo"),
        detalle("Mensualidad", estado),
    ])
    contenido += (
        '<div class="columnas"><section class="panel"><h2>Información del vehículo</h2>'
        '<dl class="datos">' + datos + '</dl></section><section>'
    )
    if cotizacion is None:
        contenido += '<p class="error aviso">Reactiva al cliente y al vehículo para registrar pagos.</p>'
    else:
        campos = (
            '<h2>Registrar pago</h2>'
            + oculto("placa", vehiculo["placa"])
            + f'<div class="importe">{moneda(cotizacion["valor_centavos"])}</div>'
            '<p>Mensualidad de un mes calendario.</p>'
            '<label>Medio de pago<select name="medio" id="medio-pago">'
            '<option>Efectivo</option><option>Transferencia</option></select></label>'
            '<label id="campo-referencia" hidden>Referencia de transferencia'
            '<input name="referencia" id="referencia-pago" maxlength="250" '
            'oninvalid="this.setCustomValidity(\'Ingresa la referencia de la transferencia.\')" '
            'oninput="this.setCustomValidity(\'\')"></label>'
            '<dl class="datos">'
            + detalle("Inicio de cobertura", fecha(cotizacion["fecha_inicio"]))
            + detalle("Último día cubierto", fecha(cotizacion["ultimo_dia"]))
            + '</dl><p class="ayuda">Podrás revisar el resumen antes de guardar el pago.</p>'
        )
        contenido += formulario("pagos/revisar", token, campos, "Revisar pago")
        contenido += """
        <script>
        const medio = document.getElementById('medio-pago');
        const campo = document.getElementById('campo-referencia');
        const referencia = document.getElementById('referencia-pago');
        function actualizarReferencia() {
            const transferencia = medio.value === 'Transferencia';
            campo.hidden = !transferencia;
            referencia.required = transferencia;
            referencia.setCustomValidity('');
            if (!transferencia) referencia.value = '';
        }
        medio.addEventListener('change', actualizarReferencia);
        actualizarReferencia();
        </script>
        """
    return contenido + '</section></div>'


def resumen_pago(codigo, datos, token):
    campos = [
        ("Cliente", datos["cliente"]), ("Placa", datos["placa"]),
        ("Valor", moneda(datos["valor_centavos"])), ("Medio", datos["medio"]),
        ("Referencia", datos["referencia"] or "—"),
        ("Inicio de cobertura", fecha(datos["fecha_inicio"])),
        ("Último día cubierto", fecha(datos["ultimo_dia"])),
    ]
    contenido = (
        "<h1>Revisar y confirmar pago</h1>"
        '<section class="panel"><dl class="datos">'
        + "".join(detalle(nombre, valor) for nombre, valor in campos)
        + '</dl><p>Confirma después de verificar que recibiste el pago. '
        'El resumen tiene una vigencia de 15 minutos.</p></section>'
        + formulario("pagos/confirmar", token, oculto("solicitud", codigo), "Confirmar pago")
        + '<p><a class="boton secundaria" href="/pagos?'
        + urlencode({"placa": datos["placa"]}) + '">Volver sin registrar</a></p>'
    )
    return contenido


def comprobante_pago(codigo):
    pago = pagos.obtener_pago(codigo)
    campos = [
        ("Cliente", pago["cliente"]), ("Documento", pago["documento"]),
        ("Placa", pago["placa"]), ("Tipo de vehículo", pago["tipo_vehiculo"]),
        ("Concepto", "Mensualidad de " + pago["tipo_vehiculo"].lower()),
        ("Medio de pago", pago["medio"]), ("Referencia", pago["referencia"] or "—"),
        ("Fecha y hora del pago", fecha(pago["fecha_hora"]) + " " + pago["fecha_hora"][11:]),
        ("Inicio de cobertura", fecha(pago["fecha_inicio"])),
        ("Último día cubierto", fecha(pago["ultimo_dia"])),
        ("Registrado por", pago["nombre_operario"] + " (" + pago["usuario_operario"] + ")"),
    ]
    return (
        '<h1>Comprobante de pago</h1><p class="exito">Pago registrado correctamente.</p>'
        '<section class="panel comprobante"><header><h2>Autos Colombia</h2>'
        f'<span class="codigo">{escapar(pago["codigo_comprobante"])}</span></header>'
        '<dl class="datos">'
        + "".join(detalle(nombre, valor) for nombre, valor in campos)
        + f'</dl><div class="importe">{moneda(pago["valor_centavos"])}</div></section>'
        '<p class="acciones"><button onclick="window.print()">Imprimir comprobante</button> '
        '<a class="boton secundaria" href="/pagos">Volver a pagos</a></p>'
    )


def pagina_historial(placa, desde, hasta):
    filas = pagos.historial_pagos(placa, desde, hasta)
    cuerpo = ""
    for pago in filas:
        columnas = [
            pago["codigo_comprobante"], fecha(pago["fecha_hora"]), pago["placa"],
            moneda(pago["valor_centavos"]), pago["medio"],
            fecha(pago["fecha_inicio"]), fecha(pago["ultimo_dia"]),
            pago["usuario_operario"],
        ]
        cuerpo += (
            "<tr>" + "".join(f"<td>{escapar(valor)}</td>" for valor in columnas)
            + '<td><a href="/pagos/comprobante?'
            + urlencode({"codigo": pago["codigo_comprobante"]})
            + '">Ver comprobante</a></td></tr>'
        )
    if not cuerpo:
        cuerpo = '<tr><td colspan="9">No se encontraron pagos.</td></tr>'
    encabezados = [
        "Comprobante", "Fecha", "Placa", "Valor", "Medio",
        "Inicio", "Último día cubierto", "Responsable", "Acción",
    ]
    return (
        "<h1>Historial de pagos</h1>" + pestanas("historial")
        + '<form class="filtros" method="get" action="/pagos/historial">'
        '<label>Placa'
        f'<input name="placa" value="{escapar(placa)}" maxlength="250"></label>'
        '<label>Fecha desde'
        f'<input type="date" name="desde" value="{escapar(desde)}"></label>'
        '<label>Fecha hasta'
        f'<input type="date" name="hasta" value="{escapar(hasta)}"></label>'
        '<button>Buscar</button><a class="boton secundaria" href="/pagos/historial">'
        'Limpiar filtros</a></form>'
        '<div class="tabla"><table><thead><tr>'
        + "".join(f"<th>{nombre}</th>" for nombre in encabezados)
        + "</tr></thead><tbody>" + cuerpo + "</tbody></table></div>"
    )
