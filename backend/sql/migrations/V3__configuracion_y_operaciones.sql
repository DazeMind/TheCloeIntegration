USE [the_cloe];
GO

-- =====================================================================
-- V3 — Configuración, certificados, vistas, stored procedures y seed
-- =====================================================================

-- 1. CERTIFICADOS DIGITALES (firma electrónica por empresa)
--    El archivo NO se guarda en BD — solo se referencia (URL/storage).
--    'password_cifrada' NUNCA en claro: cifrar con AES-256 en la app.
CREATE TABLE sii_integration.certificados_digitales (
    id                BIGINT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    uuid              UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() UNIQUE,
    empresa_id        BIGINT NOT NULL,
    nombre            NVARCHAR(100) NOT NULL,
    archivo_pfx_url   NVARCHAR(500) NULL,
    password_cifrada  NVARCHAR(500) NULL,
    emisor            NVARCHAR(200) NULL,
    fecha_emision     DATE NULL,
    fecha_expiracion  DATE NOT NULL,
    activo            BIT NOT NULL DEFAULT 1,
    fecha_creacion    DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),

    CONSTRAINT FK_cert_empresa FOREIGN KEY (empresa_id)
        REFERENCES sii_integration.empresas (id) ON DELETE CASCADE
);
GO

-- 2. CONFIGURACIONES POR EMPRESA + AMBIENTE
--    Reemplaza la config global. Una empresa puede tener config testing
--    y una config producción simultáneamente — con su propio timbrado.
CREATE TABLE sii_integration.configuraciones_empresa (
    id                  BIGINT IDENTITY(1,1) PRIMARY KEY CLUSTERED,
    uuid                UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() UNIQUE,
    empresa_id          BIGINT NOT NULL,
    ambiente            NVARCHAR(20) NOT NULL DEFAULT 'testing',
    timbrado            NVARCHAR(20) NULL,
    prefijo_folio       NVARCHAR(10) NULL DEFAULT 'F',
    certificado_id      BIGINT NULL,
    activa              BIT NOT NULL DEFAULT 1,
    fecha_creacion      DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    fecha_actualizacion DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),

    CONSTRAINT FK_conf_empresa FOREIGN KEY (empresa_id)
        REFERENCES sii_integration.empresas (id) ON DELETE CASCADE,
    CONSTRAINT FK_conf_certificado FOREIGN KEY (certificado_id)
        REFERENCES sii_integration.certificados_digitales (id),
    CONSTRAINT CHK_conf_ambiente CHECK (ambiente IN ('produccion', 'testing'))
);
GO

-- Para cada empresa, solo UNA config activa por ambiente
CREATE UNIQUE NONCLUSTERED INDEX IX_conf_empresa_ambiente_activa
    ON sii_integration.configuraciones_empresa (empresa_id, ambiente)
    WHERE activa = 1;
GO

-- 3. Trigger para actualización automática de fecha en configuraciones
CREATE TRIGGER sii_integration.TRG_configuraciones_update
ON sii_integration.configuraciones_empresa
AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    UPDATE sii_integration.configuraciones_empresa
    SET fecha_actualizacion = SYSDATETIMEOFFSET()
    FROM Inserted i
    WHERE sii_integration.configuraciones_empresa.id = i.id;
END;
GO

-- 4. VISTA — Dashboard de emisiones por empresa
CREATE VIEW sii_integration.vw_resumen_emisiones_empresa AS
SELECT
    e.rut_emisor,
    e.razon_social,
    d.tipo_documento,
    d.estado,
    COUNT(d.id)                        AS total_documentos,
    SUM(d.monto_total)                 AS monto_acumulado,
    MAX(d.fecha_creacion)              AS ultima_emision,
    SUM(CASE WHEN d.estado = 'ANULADO' THEN 1 ELSE 0 END) AS total_anulados
FROM sii_integration.documentos_tributarios d
INNER JOIN sii_integration.empresas e ON d.empresa_id = e.id
GROUP BY e.rut_emisor, e.razon_social, d.tipo_documento, d.estado;
GO

-- 5. STORED PROCEDURES

-- 5.1 Registro de log de API — nunca puede fallar por el agente
CREATE PROCEDURE sii_integration.sp_registrar_log_api
    @agente_id              BIGINT = NULL,
    @idempotency_key        UNIQUEIDENTIFIER = NULL,
    @endpoint               NVARCHAR(255),
    @metodo_http            NVARCHAR(10),
    @codigo_http            INT = NULL,
    @payload                NVARCHAR(MAX) = NULL,
    @respuesta              NVARCHAR(MAX) = NULL,
    @mensaje_error          NVARCHAR(MAX) = NULL,
    @duracion_ms            INT = NULL,
    @ip_origen              NVARCHAR(45) = NULL,
    @user_agent             NVARCHAR(255) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO sii_integration.logs_consultas_api (
        agente_id, idempotency_key, endpoint, metodo_http,
        codigo_respuesta_http, payload_enviado, respuesta_recibida,
        mensaje_error, duracion_ms, ip_origen, user_agent
    ) VALUES (
        @agente_id, @idempotency_key, @endpoint, @metodo_http,
        @codigo_http, @payload, @respuesta,
        @mensaje_error, @duracion_ms, @ip_origen, @user_agent
    );
END;
GO

-- 5.2 Cambio de estado TRANSACCIONAL: histórico + documento, atómico
CREATE PROCEDURE sii_integration.sp_registrar_cambio_estado
    @documento_id   BIGINT,
    @estado_nuevo   NVARCHAR(20),
    @motivo         NVARCHAR(250) = NULL,
    @agente_id      BIGINT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @estado_anterior NVARCHAR(20);
        SELECT @estado_anterior = estado
        FROM sii_integration.documentos_tributarios
        WHERE id = @documento_id;

        IF @estado_anterior IS NULL
        BEGIN
            RAISERROR('Documento %d no existe', 16, 1, @documento_id);
            RETURN;
        END

        INSERT INTO sii_integration.historico_estados_documento (
            documento_id, estado_anterior, estado_nuevo, motivo, agente_id
        ) VALUES (
            @documento_id, @estado_anterior, @estado_nuevo, @motivo, @agente_id
        );

        UPDATE sii_integration.documentos_tributarios
        SET estado = @estado_nuevo
        WHERE id = @documento_id;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO

-- 5.3 Worker de reintentos: documentos pendientes cuyo plazo venció
CREATE PROCEDURE sii_integration.sp_listar_pendientes_reintento
    @limite INT = 100
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@limite)
        d.id, d.uuid_operacion, d.empresa_id, d.tipo_documento,
        d.rut_emisor, d.rut_receptor, d.monto_total,
        d.intentos, d.proximo_reintento
    FROM sii_integration.documentos_tributarios d
    WHERE d.estado = 'PENDIENTE'
      AND d.intentos < 5
      AND (d.proximo_reintento IS NULL OR d.proximo_reintento <= SYSDATETIMEOFFSET())
    ORDER BY d.fecha_creacion ASC;
END;
GO

-- 6. DATOS INICIALES: agente SYSTEM por defecto
INSERT INTO sii_integration.agentes_integracion (nombre, descripcion, tipo)
VALUES ('SYSTEM', 'Procesos automáticos internos', 'SISTEMA');
GO
