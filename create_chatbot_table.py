import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=host.docker.internal,1433;'
    'DATABASE=the_cloe;'
    'UID=TestLocal;'
    'PWD=TestLocal;'
    'TrustServerCertificate=yes;'
)

cursor = conn.cursor()

# Crear tabla si no existe
cursor.execute('''
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='chatbot_chatbotsession' AND xtype='U')
    CREATE TABLE chatbot_chatbotsession (
        id bigint IDENTITY(1,1) PRIMARY KEY,
        session_id varchar(40) NOT NULL UNIQUE,
        created_at datetime2 NOT NULL,
        message_count int NOT NULL DEFAULT 0,
        last_message nvarchar(max) NULL,
        last_response nvarchar(max) NULL
    )
''')
conn.commit()

# Verificar
cursor.execute('SELECT NAME FROM sys.tables WHERE name=?', 'chatbot_chatbotsession')
row = cursor.fetchone()
print('Tabla creada:', row[0] if row else 'No encontrada')

conn.close()
print('Conexión exitosa - tabla chatbot_chatbotsession asegurada')