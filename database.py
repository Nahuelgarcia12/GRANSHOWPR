import sqlite3
from typing import List, Dict, Any

DB_NAME = "trivia.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea la tabla e inserta preguntas iniciales si está vacía."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consigna TEXT NOT NULL,
            respuesta_correcta TEXT NOT NULL,
            categoria TEXT NOT NULL,
            tipo TEXT DEFAULT 'abierta'
        );
    """)

    # Comprobar si ya tiene preguntas cargadas
    cursor.execute("SELECT COUNT(*) FROM preguntas")
    if cursor.fetchone()[0] == 0:
        preguntas_semilla = [
            ("¿En qué año llegó el ser humano a la Luna en la misión Apolo 11?", "1969", "Cultura General", "abierta"),
            ("¿Qué selección de fútbol ganó el Mundial de 1986?", "Argentina", "Deportes", "abierta"),
            ("¿Cuál es el río más caudaloso del mundo?", "Amazonas", "Geografía", "abierta"),
            ("¿Quién escribió 'Cien años de soledad'?", "Gabriel García Márquez", "Literatura", "abierta"),
            ("¿Cuál es el elemento químico con el símbolo Au?", "Oro", "Ciencia", "abierta"),
            ("¿En qué año se estrenó la primera película de Toy Story?", "1995", "Cine", "abierta"),
            ("¿Cuántos huesos tiene el cuerpo humano adulto?", "206", "Ciencia", "abierta")
        ]
        cursor.executemany("""
            INSERT INTO preguntas (consigna, respuesta_correcta, categoria, tipo)
            VALUES (?, ?, ?, ?)
        """, preguntas_semilla)
        conn.commit()
        print("-> Base de datos inicializada con preguntas semilla.")

    conn.close()


def get_random_questions(limit: int = 25) -> List[Dict[str, Any]]:
    """Trae un lote de preguntas ordenadas al azar."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, consigna, respuesta_correcta, categoria, tipo FROM preguntas ORDER BY RANDOM() LIMIT ?",
                   (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def insert_question(consigna: str, respuesta: str, categoria: str, tipo: str = "abierta") -> int:
    """Inserta una pregunta nueva desde el panel."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO preguntas (consigna, respuesta_correcta, categoria, tipo)
        VALUES (?, ?, ?, ?)
    """, (consigna.strip(), respuesta.strip(), categoria.strip(), tipo))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


if __name__ == "__main__":
    init_db()