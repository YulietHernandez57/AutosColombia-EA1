PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS persona (
    id_persona INTEGER PRIMARY KEY,
    documento TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS vehiculo (
    id_vehiculo INTEGER PRIMARY KEY,
    placa TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('Moto', 'Automovil', 'Camioneta')),
    marca TEXT NOT NULL,
    modelo TEXT NOT NULL,
    color TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    id_persona INTEGER NOT NULL,
    FOREIGN KEY (id_persona) REFERENCES persona(id_persona)
);

CREATE TABLE IF NOT EXISTS mensualidad (
    id_mensualidad INTEGER PRIMARY KEY,
    fecha_inicio TEXT NOT NULL,
    fecha_vencimiento TEXT NOT NULL,
    id_vehiculo INTEGER NOT NULL,
    FOREIGN KEY (id_vehiculo) REFERENCES vehiculo(id_vehiculo),
    CHECK (fecha_vencimiento > fecha_inicio)
);

CREATE TABLE IF NOT EXISTS celda (
    id_celda INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL CHECK (tipo IN ('Moto', 'Vehiculo'))
);

CREATE TABLE IF NOT EXISTS operario (
    id_operario INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS estancia (
    id_estancia INTEGER PRIMARY KEY,
    fecha_hora_entrada TEXT NOT NULL,
    fecha_hora_salida TEXT,
    codigo_comprobante TEXT NOT NULL UNIQUE,
    id_vehiculo INTEGER NOT NULL,
    id_celda INTEGER NOT NULL,
    id_operario_entrada INTEGER NOT NULL,
    id_operario_salida INTEGER,

    FOREIGN KEY (id_vehiculo) REFERENCES vehiculo(id_vehiculo),
    FOREIGN KEY (id_celda) REFERENCES celda(id_celda),
    FOREIGN KEY (id_operario_entrada)
        REFERENCES operario(id_operario),
    FOREIGN KEY (id_operario_salida)
        REFERENCES operario(id_operario),

    CHECK (
        (fecha_hora_salida IS NULL AND id_operario_salida IS NULL)
        OR
        (fecha_hora_salida IS NOT NULL
         AND id_operario_salida IS NOT NULL
         AND fecha_hora_salida >= fecha_hora_entrada)
    )
);

CREATE TABLE IF NOT EXISTS cambio_celda (
    id_cambio INTEGER PRIMARY KEY,
    fecha_hora TEXT NOT NULL,
    motivo TEXT NOT NULL CHECK (length(trim(motivo)) > 0),
    id_estancia INTEGER NOT NULL,
    id_operario INTEGER NOT NULL,
    id_celda_anterior INTEGER NOT NULL,
    id_celda_nueva INTEGER NOT NULL,

    FOREIGN KEY (id_estancia) REFERENCES estancia(id_estancia),
    FOREIGN KEY (id_operario) REFERENCES operario(id_operario),
    FOREIGN KEY (id_celda_anterior) REFERENCES celda(id_celda),
    FOREIGN KEY (id_celda_nueva) REFERENCES celda(id_celda),

    CHECK (id_celda_anterior <> id_celda_nueva)
);

CREATE UNIQUE INDEX IF NOT EXISTS vehiculo_estancia_abierta
ON estancia(id_vehiculo)
WHERE fecha_hora_salida IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS celda_estancia_abierta
ON estancia(id_celda)
WHERE fecha_hora_salida IS NULL;

CREATE TABLE IF NOT EXISTS estado_celda (
    id_estado_celda INTEGER PRIMARY KEY,
    id_celda INTEGER NOT NULL REFERENCES celda(id_celda),
    id_operario INTEGER NOT NULL REFERENCES operario(id_operario),
    habilitada INTEGER NOT NULL CHECK (habilitada IN (0, 1)),
    motivo TEXT NOT NULL CHECK (length(trim(motivo)) > 0),
    fecha_hora TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS estado_celda_por_celda
ON estado_celda(id_celda, id_estado_celda DESC);

CREATE VIEW IF NOT EXISTS disponibilidad_celda AS
SELECT c.id_celda, c.codigo, c.tipo,
       COALESCE((
           SELECT ec.habilitada
           FROM estado_celda AS ec
           WHERE ec.id_celda = c.id_celda
           ORDER BY ec.id_estado_celda DESC
           LIMIT 1
       ), 1) AS habilitada
FROM celda AS c;

CREATE TABLE IF NOT EXISTS cuenta (
    id_operario INTEGER PRIMARY KEY REFERENCES operario(id_operario),
    rol TEXT NOT NULL CHECK (rol IN ('Administrador', 'Operario')),
    sal BLOB NOT NULL,
    clave BLOB NOT NULL,
    activa INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1))
);

CREATE TABLE IF NOT EXISTS tarifa_mensual (
    id_tarifa INTEGER PRIMARY KEY,
    tipo_celda TEXT NOT NULL CHECK (tipo_celda IN ('Moto', 'Vehiculo')),
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
    fecha_hora TEXT NOT NULL,
    id_operario INTEGER REFERENCES operario(id_operario)
);

CREATE INDEX IF NOT EXISTS tarifa_por_tipo
ON tarifa_mensual(tipo_celda, id_tarifa DESC);

CREATE TABLE IF NOT EXISTS solicitud_pago (
    codigo TEXT PRIMARY KEY,
    id_operario INTEGER NOT NULL REFERENCES operario(id_operario),
    fecha_hora TEXT NOT NULL,
    datos TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pago (
    id_pago INTEGER PRIMARY KEY,
    codigo_comprobante TEXT NOT NULL UNIQUE,
    solicitud TEXT NOT NULL UNIQUE REFERENCES solicitud_pago(codigo),
    id_mensualidad INTEGER NOT NULL UNIQUE REFERENCES mensualidad(id_mensualidad),
    id_vehiculo INTEGER NOT NULL REFERENCES vehiculo(id_vehiculo),
    id_operario INTEGER NOT NULL REFERENCES operario(id_operario),
    id_tarifa INTEGER NOT NULL REFERENCES tarifa_mensual(id_tarifa),
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
    medio TEXT NOT NULL CHECK (medio IN ('Efectivo', 'Transferencia')),
    referencia TEXT NOT NULL,
    fecha_hora TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    ultimo_dia TEXT NOT NULL CHECK (ultimo_dia >= fecha_inicio),
    placa TEXT NOT NULL,
    cliente TEXT NOT NULL,
    documento TEXT NOT NULL,
    tipo_vehiculo TEXT NOT NULL,
    nombre_operario TEXT NOT NULL,
    usuario_operario TEXT NOT NULL,
    CHECK (medio <> 'Transferencia' OR length(trim(referencia)) > 0)
);

CREATE INDEX IF NOT EXISTS pago_por_fecha ON pago(fecha_hora);
CREATE INDEX IF NOT EXISTS pago_por_placa ON pago(placa, fecha_hora);
