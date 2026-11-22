"""Pruebas de pagos aisladas. Ejecutar: py verificar_pagos.py.

No usa ni modifica autos_colombia.db del proyecto. Crea una base desechable
en un directorio temporal y llama a las funciones de negocio del servidor.
No automatiza el navegador ni certifica su presentación visual.
"""
import json
import secrets
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


def ejecutar_pruebas():
    import app  # Inicializa únicamente la copia temporal.
    import cuentas
    import datos_prueba
    import pagos
    from datetime import date, timedelta

    cuentas.crear_cuenta('admin_test', 'Administrador de prueba', secrets.token_urlsafe(24), 'Administrador')
    cuentas.crear_cuenta('operario_test', 'Operario de prueba', secrets.token_urlsafe(24), 'Operario')
    resultados = []

    def comprobar(caso, nombre, accion):
        try:
            detalle = accion()
            resultados.append(dict(caso=caso, prueba=nombre, estado='Aprobado', resultado=detalle))
        except Exception as error:
            resultados.append(dict(caso=caso, prueba=nombre, estado='Fallido', resultado=str(error)))

    contexto = {}

    def transferencia():
        solicitud, datos = pagos.preparar_pago('NEW123', 'Transferencia', 'PRUEBA-TR-001', 'operario_test')
        codigo = pagos.confirmar_pago(solicitud, 'operario_test')
        pago = pagos.obtener_pago(codigo)
        assert pago['medio'] == 'Transferencia' and pago['referencia'] == 'PRUEBA-TR-001'
        assert pago['valor_centavos'] == 20000000
        contexto.update(solicitud=solicitud, codigo=codigo, pago=pago)
        return 'Transferencia guardada con referencia y comprobante en base temporal.'

    def renovacion():
        anterior = contexto['pago']
        solicitud, datos = pagos.preparar_pago('NEW123', 'Efectivo', '', 'admin_test')
        esperado = date.fromisoformat(anterior['ultimo_dia']) + timedelta(days=1)
        assert datos['fecha_inicio'] == esperado.isoformat()
        codigo = pagos.confirmar_pago(solicitud, 'admin_test')
        nuevo = pagos.obtener_pago(codigo)
        assert nuevo['fecha_inicio'] == esperado.isoformat()
        assert nuevo['ultimo_dia'] == pagos.fin_de_mes_pagado(esperado).isoformat()
        return 'Renovación confirmada desde el día siguiente al último cubierto, sin superposición.'

    def duplicado():
        antes = len(pagos.historial_pagos('NEW123'))
        codigo = pagos.confirmar_pago(contexto['solicitud'], 'operario_test')
        assert codigo == contexto['codigo']
        assert len(pagos.historial_pagos('NEW123')) == antes
        return 'Reenviar la misma confirmación devuelve el comprobante existente sin otro pago.'

    def valor_historico():
        anterior = pagos.obtener_pago(contexto['codigo'])
        pagos.actualizar_tarifas('90000', '250000', 'admin_test')
        assert pagos.obtener_pago(contexto['codigo']) == anterior
        with pagos.conectar() as conexion:
            assert pagos.cotizar(conexion, 'NEW123')['valor_centavos'] == 25000000
        return 'Comprobante anterior conserva 200000 COP; una nueva cotización usa 250000 COP.'

    def operario():
        pago = pagos.obtener_pago(contexto['codigo'])
        assert pago['usuario_operario'] == 'operario_test'
        try:
            pagos.actualizar_tarifas('1', '1', 'operario_test')
        except ValueError:
            pass
        else:
            raise AssertionError('El operario pudo modificar tarifas.')
        return 'Pago registrado por operario_test; modificación de tarifas denegada al operario.'

    def fechas():
        fecha = contexto['pago']['fecha_hora'][:10]
        encontrados = pagos.historial_pagos('NEW123', fecha, fecha)
        assert any(p['codigo_comprobante'] == contexto['codigo'] for p in encontrados)
        assert not pagos.historial_pagos('NEW123', '2000-01-01', '2000-01-02')
        return 'Filtro inclusivo encuentra el pago en su fecha y lo excluye de un intervalo sin pagos.'

    def validacion_servidor():
        def totales():
            with pagos.conectar() as conexion:
                return tuple(conexion.execute('SELECT COUNT(*) FROM ' + tabla).fetchone()[0]
                             for tabla in ('tarifa_mensual', 'solicitud_pago', 'pago', 'mensualidad'))
        antes = totales()
        for accion in (
            lambda: pagos.actualizar_tarifas('0', '200000', 'admin_test'),
            lambda: pagos.preparar_pago('NEW123', 'Transferencia', '', 'admin_test'),
        ):
            try:
                accion()
            except ValueError:
                pass
            else:
                raise AssertionError('Se aceptaron datos inválidos.')
        assert totales() == antes
        return 'Funciones del servidor rechazan tarifa cero y transferencia sin referencia; conteos sin cambios.'

    for datos in (
        ('PG-17', 'Transferencia válida', transferencia),
        ('PG-18', 'Renovación anticipada', renovacion),
        ('PG-19', 'Confirmación sin duplicado', duplicado),
        ('PG-20', 'Conservación del valor histórico', valor_historico),
        ('PG-21', 'Registro por operario', operario),
        ('PG-22', 'Filtro por fechas', fechas),
        ('PG-23', 'Validaciones en funciones del servidor', validacion_servidor),
    ):
        comprobar(*datos)
    return resultados


def main():
    carpeta = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='autos_colombia_pruebas_') as temporal:
        destino = Path(temporal)
        for nombre in ('app.py', 'schema.sql', 'cuentas.py', 'datos_prueba.py', 'pagos.py', 'verificar_pagos.py'):
            shutil.copy2(carpeta / nombre, destino / nombre)
        salida_temporal = destino / 'resultado.json'
        ejecucion = subprocess.run(
            [sys.executable, str(destino / 'verificar_pagos.py'), '--aislado', str(salida_temporal)],
            capture_output=True, text=True,
        )
        if ejecucion.returncode or not salida_temporal.exists():
            raise SystemExit('No fue posible completar las pruebas: ' + ejecucion.stderr)
        resultados = json.loads(salida_temporal.read_text(encoding='utf-8'))
    informe = {
        'fecha_ejecucion': datetime.now().isoformat(timespec='seconds'),
        'tipo': 'Automáticas: funciones de negocio del servidor, no navegador ni HTTP.',
        'entorno': 'Base temporal nueva, datos ficticios. Base del usuario no utilizada.',
        'resultados': resultados,
    }
    ruta = carpeta / 'Resultado_Pruebas_Automaticas_Pagos.json'
    ruta.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
    for resultado in resultados:
        print(f"{resultado['caso']}: {resultado['estado']} - {resultado['prueba']}")
    print('Informe: ' + str(ruta))
    print('Tu base de datos y tus pagos no se modificaron.')
    return 0 if all(r['estado'] == 'Aprobado' for r in resultados) else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--aislado':
        Path(sys.argv[2]).write_text(json.dumps(ejecutar_pruebas(), ensure_ascii=False), encoding='utf-8')
    else:
        raise SystemExit(main())
