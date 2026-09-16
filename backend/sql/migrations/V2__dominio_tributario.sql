USE [the_cloe];
GO

-- =====================================================================
-- V2 — Dominio tributario: DTE, detalles, histórico de estados, logs IA
-- =====================================================================

-- 1. DOCUMENTOS TRIBUTARIOS (DTE)
--    - uuid_operacion: id interno global (UUID) — evita colisiones multi-empresa
--    - id_venta_origen: id de correlación con el sistema privado
--    - fecha_emision:   fecha comercial del documento (la pone el negocio)
--    - fecha_creacion:  cuándo se registró aquí (la pone el sistema)
CREATE TABLE sii_integration.documentos_tributarios (
    id                    BIGINT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    uuid                  UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() UNIQUE,
    uuid_operacion        UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    empresa_id            BIGINT NOT NULL,
    id_venta_origen       NVARCHAR(100) NOT NULL,

    tipo_documento        INT NOT NULL DEFAULT 39,
    folio                 INT NULL,
    track_id              NVARCHAR(100) NULL,

    rut_emisor            NVARCHAR(12) NOT NULL,
    rut_receptor          NVARCHAR(12) NOT NULL,
    razon_social_receptor NVARCHAR(200) NULL,
    monto_total           DECIMAL(12, 2) NOT NULL,

    estado                NVARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',

    pdf_url               NVARCHAR(500) NULL,
    xml_url               NVARCHAR(500) NULL,
    respuesta_sii_json    NVARCHAR(MAX) NULL,
    codigo_estado_sii     INT NULL,
    glosa_estado_sii      NVARCHAR(255) NULL,

    -- Anulación / Referencia (SII: RefTipoDoc, RefFolio, RefFecha)
    documento_referencia_id BIGINT NULL,
    tipo_referencia       INT NULL,
    fecha_referencia      DATETIMEOFFSET NULL,
    motivo_anulacion      NVARCHAR(250) NULL,

    -- Resiliencia (retry worker)
    intentos              INT NOT NULL DEFAULT 0,
    proximo_reintento     DATETIMEOFFSET NULL,

    fecha_emision         DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    fecha_creacion        DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    fecha_actualizacion   DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),

    CONSTRAINT FK_doc_empresa FOREIGN KEY (empresa_id)
        REFERENCES sii_integration.empresas (id),
    CONSTRAINT FK_doc_referencia FOREIGN KEY (documento_referencia_id)
        REFERENCES sii_integration.documentos_tributarios (id),
    CONSTRAINT CHK_doc_estado CHECK (estado IN ('PENDIENTE', 'ENVIADO', 'ACEPTADO', 'RECHAZADO', 'ANULADO', 'ERROR')),
    CONSTRAINT CHK_doc_tipo CHECK (tipo_documento IN (33, 34, 35, 38, 39, 41, 46, 52, 56, 61)),
    CONSTRAINT CHK_doc_respuesta_json CHECK (respuesta_sii_json IS NULL OR ISJSON(respuesta_sii_json) = 1),
    CONSTRAINT CHK_doc_monto_positivo CHECK (monto_total >= 0),

    -- Idempotencia: mismo id_venta_origen + mismo tipo = mismo documento (por empresa)
    CONSTRAINT UQ_empresa_venta_tipo UNIQUE (empresa_id, id_venta_origen, tipo_documento)
);
GO

-- 2. DETALLES DEL DOCUMENTO (ítems vendidos — normalizados)
CREATE TABLE sii_integration.detalles_documento (
    id                BIGINT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    documento_id      BIGINT NOT NULL,
    linea             INT NOT NULL,
    nombre_producto   NVARCHAR(200) NOT NULL,
    codigo_producto   NVARCHAR(50) NULL,
    cantidad          DECIMAL(12, 4) NOT NULL DEFAULT 1,
    precio_unitario   DECIMAL(12, 2) NOT NULL,
    monto_linea       DECIMAL(12, 2) NOT NULL,

    CONSTRAINT FK_detalle_documento FOREIGN KEY (documento_id)
        REFERENCES sii_integration.documentos_tributarios (id) ON DELETE CASCADE,
    CONSTRAINT CHK_detalle_cantidad CHECK (cantidad > 0),
    CONSTRAINT CHK_detalle_precio CHECK (precio_unitario >= 0),
    CONSTRAINT CHK_detalle_monto CHECK (monto_linea >= 0),
    CONSTRAINT UQ_detalle_linea UNIQUE (documento_id, linea)
);
GO

-- 3. HISTÓRICO DE ESTADOS (auditoría de transiciones)
CREATE TABLE sii_integration.historico_estados_documento (
    id               BIGINT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    documento_id     BIGINT NOT NULL,
    estado_anterior  NVARCHAR(20) NULL,
    estado_nuevo     NVARCHAR(20) NOT NULL,
    motivo           NVARCHAR(250) NULL,
    agente_id        BIGINT NULL,
    fecha_cambio     DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),

    CONSTRAINT FK_hist_documento FOREIGN KEY (documento_id)
        REFERENCES sii_integration.documentos_tributarios (id) ON DELETE CASCADE,
    CONSTRAINT FK_hist_agente FOREIGN KEY (agente_id)
        REFERENCES sii_integration.agentes_integracion (id) ON DELETE SET NULL
);
GO

-- 4. LOGS DE CONSULTAS A IA
--    Persistencia de resultados y auditoría de las llamadas a modelos
--    de IA integrados (proveedor, modelo, prompt, respuesta, tokens,
--    duración, costo estimado y errores). Totalmente desacoplado del
--    dominio tributario: la IA puede fallar sin afectar nada más.
CREATE TABLE sii_integration.logs_consultas_ia (
    id                    BIGINT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    uuid                  UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() UNIQUE,
    agente_id             BIGINT NULL,
    proveedor_ia          NVARCHAR(50) NOT NULL,
    modelo                NVARCHAR(100) NULL,
    endpoint              NVARCHAR(255) NULL,
    prompt_enviado        NVARCHAR(MAX) NULL,
    respuesta_recibida    NVARCHAR(MAX) NULL,
    mensaje_error         NVARCHAR(MAX) NULL,
    tokens_prompt         INT NULL,
    tokens_completado     INT NULL,
    duracion_ms           INT NULL,
    codigo_respuesta_http INT NULL,
    costo_estimado        DECIMAL(12, 6) NULL,
    metadata_json         NVARCHAR(MAX) NULL,
    fecha_consulta        DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),

    CONSTRAINT FK_logs_ia_agente FOREIGN KEY (agente_id)
        REFERENCES sii_integration.agentes_integracion (id) ON DELETE SET NULL,
    CONSTRAINT CHK_log_ia_metadata_json CHECK (metadata_json IS NULL OR ISJSON(metadata_json) = 1)
);
GO

-- 5. Índices del dominio tributario
CREATE NONCLUSTERED INDEX IX_doc_empresa_estado
    ON sii_integration.documentos_tributarios (empresa_id, estado, fecha_creacion DESC);

CREATE NONCLUSTERED INDEX IX_doc_reintentos
    ON sii_integration.documentos_tributarios (estado, proximo_reintento)
    WHERE estado = 'PENDIENTE' AND proximo_reintento IS NOT NULL;

CREATE NONCLUSTERED INDEX IX_doc_receptor
    ON sii_integration.documentos_tributarios (empresa_id, rut_receptor);

CREATE NONCLUSTERED INDEX IX_doc_track_id
    ON sii_integration.documentos_tributarios (track_id)
    WHERE track_id IS NOT NULL;

CREATE NONCLUSTERED INDEX IX_hist_documento
    ON sii_integration.historico_estados_documento (documento_id, fecha_cambio DESC);

CREATE NONCLUSTERED INDEX IX_detalle_documento
    ON sii_integration.detalles_documento (documento_id, linea);

CREATE NONCLUSTERED INDEX IX_logs_ia_fecha
    ON sii_integration.logs_consultas_ia (fecha_consulta DESC);

CREATE NONCLUSTERED INDEX IX_logs_ia_proveedor
    ON sii_integration.logs_consultas_ia (proveedor_ia, fecha_consulta DESC);

CREATE NONCLUSTERED INDEX IX_logs_ia_agente
    ON sii_integration.logs_consultas_ia (agente_id, fecha_consulta DESC)
    WHERE agente_id IS NOT NULL;
GO

-- 6. Trigger para actualización automática de fecha en documentos
CREATE TRIGGER sii_integration.TRG_doc_tributarios_update
ON sii_integration.documentos_tributarios
AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    UPDATE sii_integration.documentos_tributarios
    SET fecha_actualizacion = SYSDATETIMEOFFSET()
    FROM Inserted i
    WHERE sii_integration.documentos_tributarios.id = i.id;
END;
GO
