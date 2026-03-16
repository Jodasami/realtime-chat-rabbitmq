Para Poder ejecutar el programa se deben cambiar las siguientes líneas de código por credenciales de PostgresSql:

Clase: pythonBD.py  (Líneas de la 30 - 34)

# ------------------------------------------- POSTGRESQL (PARAMETROS) -------------------------------------------

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB   = os.getenv("PG_DB", "Chat_DB")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASS = os.getenv("PG_PASSWORD", "Zvexnm40")

# ---------------------------------------------------------------------------------------------------------------


Clase: chat_gui.py (Líneas de la 349 - 359)

# ------------------------------------------- POSTGRESQL (PARAMETROS) -------------------------------------------
    try:
        conn = psycopg.connect(
        host=os.getenv("PG_HOST",     "localhost"),
        port=os.getenv("PG_PORT",     "5432"),
        dbname=os.getenv("PG_DB",     "Chat_DB"),
        user=os.getenv("PG_USER",     "postgres"),
        password=os.getenv("PG_PASSWORD", "admin"),
        connect_timeout=5
    )
# ---------------------------------------------------------------------------------------------------------------

Adicionalmente es necesario tener instalado el servicio de RabbitMQ.

