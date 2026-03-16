import os
import threading
from datetime import datetime

import pika
import psycopg # Para conectarse a PostgreSQL
from dotenv import load_dotenv


# ------------------------------------------- CARGAR VARIABLES DE ENTORNO -------------------------------------------

load_dotenv()

# -------------------------------------------------------------------------------------------------------------------



# ------------------------------------------- RABBITMQ (PARAMETROS) -------------------------------------------

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE_SEND = "python_to_java_queue"
QUEUE_RECEIVE = "java_to_python_queue"

# -------------------------------------------------------------------------------------------------------------



# ------------------------------------------- POSTGRESQL (PARAMETROS) -------------------------------------------

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB   = os.getenv("PG_DB", "Chat_DB")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASS = os.getenv("PG_PASSWORD", "admin")

# ---------------------------------------------------------------------------------------------------------------



# ------------------------------------------- CONEXION PostgreSQL -------------------------------------------

def get_conn():
    return psycopg.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        connect_timeout=5
    )

# -----------------------------------------------------------------------------------------------------------



# ------------------------------------------- GUARDAR MENSAJES -------------------------------------------

def save_message(sender: str, receiver: str, message: str):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO messages (sender, receiver, message, timestamp)
            VALUES (%s, %s, %s, NOW())
            """,
            (sender, receiver, message)
        )

        conn.commit()

    except Exception as e:
        print(f"  Error guardando en PostgreSQL: {e!r}")

    finally:
        if conn:
            conn.close()

# -----------------------------------------------------------------------------------------------------------



# ------------------------------------------- RECUPERAR HISTORIAL -------------------------------------------

def fetch_history(limit: int = 50):
    """Recupera los ultimos mensajes ordenados cronologicamente."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, sender, receiver, message,
                COALESCE(status, 'sent') AS status,
                timestamp
                FROM   messages
                ORDER  BY timestamp DESC
                LIMIT  %s
                """,
                (limit,)
            ).fetchall()
        return list(reversed(rows))
    except Exception as e:
        print(f"  Error leyendo historial: {e!r}")
        return []

# -----------------------------------------------------------------------------------------------------------



# ------------------------------------------- RABBITMQ: CONSUMIDOR -------------------------------------------

def start_consumer(on_message):
    """Consume mensajes de la cola y los guarda como recibidos desde Java."""
    try:
        params = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            heartbeat=30,
            blocked_connection_timeout=300,
        )
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_RECEIVE)

        def callback(ch, method, properties, body):
            msg = body.decode("utf-8", errors="replace")
            print(f" [Java→Python] recibido: {msg}")
            save_message(sender="Java", receiver="Python", message=msg)
        
            if on_message:
                on_message("Java", msg)

        channel.basic_consume(queue=QUEUE_RECEIVE, on_message_callback=callback, auto_ack=True)
        threading.Thread(
    target=channel.start_consuming,
    daemon=True
).start()
    except Exception as e:
        print(f" Error en consumidor RabbitMQ: {e!r}")

# -------------------------------------------------------------------------------------------------------------



# ------------------------------------------- RABBITMQ: PRODUCTOR -------------------------------------------

def send_to_queue(text: str):
    """Publica un mensaje en la cola y lo guarda como enviado a Java."""
    connection = None
    try:
        params = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            heartbeat=30,
            blocked_connection_timeout=300,
        )
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_SEND, durable=False)

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_SEND,
            body=text.encode("utf-8")
        )
        
        print(f" [Python→Java] enviado: {text}")
        save_message(sender="Python", receiver="Java", message=text)
    except Exception as e:
        print(f" Error publicando en RabbitMQ: {e!r}")
    finally:
        if connection:
            connection.close()

# --------------------------------------------------------------------------------------------------------------



# ------------------------------------------- MAIN -------------------------------------------

if __name__ == "__main__":
    # 1) Probar conexion PostgreSQL
    try:
        with get_conn() as _:
            print(" Conectado a PostgreSQL (prueba OK)")
    except Exception as e:
        print(f" No fue posible conectar a PostgreSQL: {e!r}")
        raise SystemExit(1)

    # 2) Lanzar consumidor en un hilo (escucha lo que envia Java)
    # t = threading.Thread(target=start_consumer, daemon=True)
    # t.start()

    # 3) Lanzar GUI
    from chat_gui import ChatApp
    app = ChatApp()
    app.mainloop()

    print(" Fin.")

# -----------------------------------------------------------------------------------------------