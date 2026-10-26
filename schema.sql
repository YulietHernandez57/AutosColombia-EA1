PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS persona (
    id_persona INTEGER PRIMARY KEY,
    documento TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vehiculo (
    id_vehiculo INTEGER PRIMARY KEY,
    placa TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('Moto', 'Automovil', 'Camioneta')),
    marca TEXT NOT NULL,
    modelo TEXT NOT NULL,
    color TEXT NOT NULL,
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