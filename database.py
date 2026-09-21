import sqlite3
import json
from typing import List, Dict, Any, Optional

DB_NAME = "trivia.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _asegurar_columna_opciones(cursor):
    """Si la tabla ya existía sin la columna 'opciones', la agrega
    sin tocar ni alterar las preguntas ya existentes."""
    cursor.execute("PRAGMA table_info(preguntas)")
    columnas = [fila[1] for fila in cursor.fetchall()]
    if "opciones" not in columnas:
        cursor.execute("ALTER TABLE preguntas ADD COLUMN opciones TEXT")


def init_db():
    """Crea la tabla e inserta preguntas iniciales solo si está vacía."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consigna TEXT NOT NULL,
            respuesta_correcta TEXT NOT NULL,
            categoria TEXT NOT NULL,
            tipo TEXT DEFAULT 'abierta',
            opciones TEXT
        );
    """)

    _asegurar_columna_opciones(cursor)

    # Comprobar si ya tiene preguntas cargadas (no sobreescribe tus 300 preguntas)
    cursor.execute("SELECT COUNT(*) FROM preguntas")
    if cursor.fetchone()[0] == 0:
        preguntas_semilla = [
            ("¿En qué año llegó el ser humano a la Luna en la misión Apolo 11?", "1969", "Cultura General", "abierta", None),
            ("¿Qué selección de fútbol ganó el Mundial de 1986?", "Argentina", "Deportes", "abierta", None),
            ("¿Cuál es el río más caudaloso del mundo?", "Amazonas", "Geografía", "abierta", None),
            ("¿Quién escribió 'Cien años de soledad'?", "Gabriel García Márquez", "Literatura", "abierta", None),
            ("¿Cuál es el elemento químico con el símbolo Au?", "Oro", "Ciencia", "abierta", None),
            ("¿En qué año se estrenó la primera película de Toy Story?", "1995", "Cine", "abierta", None),
            ("¿Cuántos huesos tiene el cuerpo humano adulto?", "206", "Ciencia", "abierta", None)
        ]
        cursor.executemany("""
            INSERT INTO preguntas (consigna, respuesta_correcta, categoria, tipo, opciones)
            VALUES (?, ?, ?, ?, ?)
        """, preguntas_semilla)
        conn.commit()
        print("-> Base de datos inicializada con preguntas semilla.")

    conn.close()


def get_next_question_excluding(excluded_ids: set) -> Optional[Dict[str, Any]]:
    """Trae una única pregunta aleatoria omitiendo los IDs ya jugados (flujo continuo sin repetición)."""
    conn = get_connection()
    cursor = conn.cursor()

    if excluded_ids:
        placeholders = ",".join("?" * len(excluded_ids))
        query = f"""
            SELECT id, consigna, respuesta_correcta, categoria, tipo, opciones 
            FROM preguntas 
            WHERE id NOT IN ({placeholders}) 
            ORDER BY RANDOM() LIMIT 1
        """
        cursor.execute(query, list(excluded_ids))
    else:
        cursor.execute("""
            SELECT id, consigna, respuesta_correcta, categoria, tipo, opciones 
            FROM preguntas 
            ORDER BY RANDOM() LIMIT 1
        """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    item = dict(row)
    if item.get("opciones"):
        try:
            item["opciones"] = json.loads(item["opciones"])
        except (json.JSONDecodeError, TypeError):
            item["opciones"] = None

    return item


def get_random_questions(limit: int = 25) -> List[Dict[str, Any]]:
    """Trae un lote de preguntas ordenadas al azar con soporte de deserialización JSON."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, consigna, respuesta_correcta, categoria, tipo, opciones FROM preguntas ORDER BY RANDOM() LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()

    resultado = []
    for row in rows:
        item = dict(row)
        if item.get("opciones"):
            try:
                item["opciones"] = json.loads(item["opciones"])
            except (json.JSONDecodeError, TypeError):
                item["opciones"] = None
        resultado.append(item)
    return resultado


def insert_question(
    consigna: str,
    respuesta: str,
    categoria: str,
    tipo: str = "abierta",
    opciones: Optional[List[str]] = None
) -> int:
    """Inserta una pregunta nueva soportando formato abierta o multiple choice."""
    conn = get_connection()
    cursor = conn.cursor()
    opciones_json = json.dumps(opciones) if opciones else None
    cursor.execute("""
        INSERT INTO preguntas (consigna, respuesta_correcta, categoria, tipo, opciones)
        VALUES (?, ?, ?, ?, ?)
    """, (consigna.strip(), respuesta.strip(), categoria.strip(), tipo, opciones_json))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


if __name__ == "__main__":
    init_db()