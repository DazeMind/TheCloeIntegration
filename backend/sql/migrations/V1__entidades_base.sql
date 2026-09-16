USE [the_cloe];
GO

-- =====================================================================
-- V1 — Entidades base: esquema, empresas, agentes, logs de API
-- The Cloe / SimpleAPI (SII Chile) — Multi-empresa, trazabilidad total
-- =====================================================================

-- 1. Esquema
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'sii_integration')
    EXEC('CREATE SCHEMA [sii_integration]');
GO

-- 2. EMPRESAS / EMISORES (multi-empresa)
--    El ambiente NO vive aquí: vive en configuraciones_empresa (V3),
--    porque una misma empresa puede estar en testing y producción.
CREATE TABLE sii_integration.empresas (
    id                  BIGINT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    uuid                UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() UNIQUE,
    rut_emisor          NVARCHAR(12) NOT NULL UNIQUE,
    razon_social        NVARCHAR(200) NOT NULL,
    nombre_fantasia     NVARCHAR(200) NULL,
    giro                NVARCHAR(200) NULL,
    email               NVARCHAR(150) NULL,
    telefono            NVARCHAR(20) NULL,
    direccion           NVARCHAR(200) NULL,
    comuna              NVARCHAR(100) NULL,
    ciudad              NVARCHAR(100) NULL,
    region              NVARCHAR(100) NULL,
    codigo_postal       NVARCHAR(10) NULL,
    activa              BIT NOT NULL DEFAULT 1,
    fecha_creacion      DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    fecha_actualizacion DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),

    CONSTRAINT CHK_empresa_rut CHECK (LEN(rut_emisor) BETWEEN 8 AND 12)
);
GO

-- 3. AGENTES DE INTEGRACIÓN
--    Quién o qué servicio realiza las consultas a la API o a la IA.
CREATE TABLE sii_integration.agentes_integracion (
    id                  BIGINT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    uuid                UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() UNIQUE,
    nombre              NVARCHAR(100) NOT NULL UNIQUE,
    descripcion         NVARCHAR(255) NULL,
    tipo                NVARCHAR(20) NOT NULL DEFAULT 'SISTEMA',
    activo              BIT NOT NULL DEFAULT 1,
    fecha_creacion      DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),

    CONSTRAINT CHK_agente_tipo CHECK (tipo IN ('SISTEMA', 'USUARIO'))
);
GO

-- 4. LOGS DE CONSULTAS API — TOTALMENTE DESACOPLADO
--    Un log registra la CONSULTA, no el documento. La consulta puede
--    fallar sin haber creado DTE: el log DEBE poder escribirse igual.
CREATE TABLE sii_integration.logs_consultas_api (
    id                   BIGINT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    uuid                 UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() UNIQUE,
    agente_id            BIGINT NULL,
    idempotency_key      UNIQUEIDENTIFIER NULL,
    endpoint             NVARCHAR(255) NOT NULL,
    metodo_http          NVARCHAR(10) NOT NULL,
    codigo_respuesta_http INT NULL,
    payload_enviado      NVARCHAR(MAX) NULL,
    respuesta_recibida   NVARCHAR(MAX) NULL,
    mensaje_error        NVARCHAR(MAX) NULL,
    duracion_ms          INT NULL,
    ip_origen            NVARCHAR(45) NULL,
    user_agent           NVARCHAR(255) NULL,
    fecha_consulta       DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),

    CONSTRAINT FK_logs_agente FOREIGN KEY (agente_id)
        REFERENCES sii_integration.agentes_integracion (id) ON DELETE SET NULL,
    CONSTRAINT CHK_log_payload_json CHECK (payload_enviado IS NULL OR ISJSON(payload_enviado) = 1),
    CONSTRAINT CHK_log_respuesta_json CHECK (respuesta_recibida IS NULL OR ISJSON(respuesta_recibida) = 1),
    CONSTRAINT CHK_log_metodo CHECK (metodo_http IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'))
);
GO

-- 5. Índices de las entidades base
CREATE NONCLUSTERED INDEX IX_logs_fecha
    ON sii_integration.logs_consultas_api (fecha_consulta DESC);

CREATE NONCLUSTERED INDEX IX_logs_agente
    ON sii_integration.logs_consultas_api (agente_id, fecha_consulta DESC)
    WHERE agente_id IS NOT NULL;
GO

-- 6. Trigger para actualización automática de fecha en empresas
CREATE TRIGGER sii_integration.TRG_empresas_update
ON sii_integration.empresas
AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    UPDATE sii_integration.empresas
    SET fecha_actualizacion = SYSDATETIMEOFFSET()
    FROM Inserted i
    WHERE sii_integration.empresas.id = i.id;
END;
GO
