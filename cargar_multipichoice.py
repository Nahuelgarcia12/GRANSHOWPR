import sqlite3
from database import insert_question, init_db, DB_NAME

# Cada ítem: (consigna, respuesta_correcta, categoria, tipo, opciones)
PREGUNTAS_MULTIPLE_CHOICE = [

    # -------------------------------------------------------------
    # 1. DEPORTES (10 preguntas)
    # -------------------------------------------------------------
    ("¿Qué selección de fútbol ganó el Mundial de Sudáfrica 2010?", "España", "Deportes", "multiple",
     ["España", "Holanda", "Alemania", "Brasil"]),
    ("¿Cuántos jugadores conforman un quinteto de básquet en cancha por equipo?", "5", "Deportes", "multiple",
     ["4", "5", "6", "7"]),
    ("¿Qué tenista masculino ostenta el récord de más títulos de Roland Garros?", "Rafael Nadal", "Deportes", "multiple",
     ["Rafael Nadal", "Roger Federer", "Novak Djokovic", "Carlos Alcaraz"]),
    ("¿En qué equipo de Fórmula 1 debutó oficialmente Franco Colapinto?", "Williams", "Deportes", "multiple",
     ["Williams", "Alpine", "Sauber", "Haas"]),
    ("¿Cuántos puntos otorga un try en rugby?", "5 puntos", "Deportes", "multiple",
     ["3 puntos", "4 puntos", "5 puntos", "6 puntos"]),
    ("¿En qué ciudad nació Lionel Messi?", "Rosario", "Deportes", "multiple",
     ["Rosario", "Santa Fe Capital", "Córdoba", "Buenos Aires"]),
    ("¿Cuántos minutos reglamentarios dura un partido de fútbol profesional?", "90 minutos", "Deportes", "multiple",
     ["80 minutos", "90 minutos", "100 minutos", "120 minutos"]),
    ("¿Qué país ganó el primer Mundial de Fútbol de la historia en 1930?", "Uruguay", "Deportes", "multiple",
     ["Uruguay", "Argentina", "Brasil", "Italia"]),
    ("¿Con qué dorsal se inmortalizó Michael Jordan en los Chicago Bulls?", "23", "Deportes", "multiple",
     ["23", "24", "32", "33"]),
    ("¿Cuántos rounds como máximo dura un combate de boxeo profesional por título del mundo?", "12", "Deportes", "multiple",
     ["10", "12", "15", "8"]),

    # -------------------------------------------------------------
    # 2. CINE Y SERIES (10 preguntas)
    # -------------------------------------------------------------
    ("¿Quién dirigió películas icónicas como 'Jurassic Park' y 'Tiburón'?", "Steven Spielberg", "Cine y Series", "multiple",
     ["Steven Spielberg", "James Cameron", "George Lucas", "Martin Scorsese"]),
    ("¿Qué actor personificó a Neo en la saga de ciencia ficción 'Matrix'?", "Keanu Reeves", "Cine y Series", "multiple",
     ["Keanu Reeves", "Brad Pitt", "Tom Cruise", "Will Smith"]),
    ("¿En qué año se estrenó en cines la primera película animada de 'Toy Story'?", "1995", "Cine y Series", "multiple",
     ["1993", "1994", "1995", "1997"]),
    ("¿Cómo se llama la cafetería donde se reunían los protagonistas en 'Friends'?", "Central Perk", "Cine y Series", "multiple",
     ["Central Perk", "Monk's Diner", "MacLaren's", "Café Nervosa"]),
    ("¿Qué actor protagonizó la película argentina 'El secreto de sus ojos'?", "Ricardo Darín", "Cine y Series", "multiple",
     ["Ricardo Darín", "Guillermo Francella", "Leonardo Sbaraglia", "Diego Peretti"]),
    ("¿Cómo se llama el villano tenebroso de la saga 'Harry Potter'?", "Lord Voldemort", "Cine y Series", "multiple",
     ["Lord Voldemort", "Severus Snape", "Gellert Grindelwald", "Lucius Malfoy"]),
    ("¿En qué ciudad ficticia vive Batman?", "Ciudad Gótica", "Cine y Series", "multiple",
     ["Ciudad Gótica", "Metrópolis", "Star City", "Central City"]),
    ("¿Quién interpretó a Michael Scott en la versión estadounidense de 'The Office'?", "Steve Carell", "Cine y Series", "multiple",
     ["Steve Carell", "Ricky Gervais", "Rainn Wilson", "John Krasinski"]),
    ("¿Cuál es el nombre de pila con el que creció Superman en la Tierra?", "Clark Kent", "Cine y Series", "multiple",
     ["Clark Kent", "Bruce Wayne", "Peter Parker", "Barry Allen"]),
    ("¿Quién protagonizó 'Forrest Gump' en el año 1994?", "Tom Hanks", "Cine y Series", "multiple",
     ["Tom Hanks", "Robin Williams", "Kevin Costner", "Mel Gibson"]),

    # -------------------------------------------------------------
    # 3. MÚSICA (10 preguntas)
    # -------------------------------------------------------------
    ("¿Qué álbum de Michael Jackson es el disco más vendido de la historia?", "Thriller", "Música", "multiple",
     ["Thriller", "Bad", "Off the Wall", "Dangerous"]),
    ("¿Quién fue el legendario cantante y líder de la banda Queen?", "Freddie Mercury", "Música", "multiple",
     ["Freddie Mercury", "Brian May", "Mick Jagger", "David Bowie"]),
    ("¿Cuántas teclas en total tiene un piano acústico tradicional?", "88 teclas", "Música", "multiple",
     ["76 teclas", "84 teclas", "88 teclas", "92 teclas"]),
    ("¿De qué ciudad inglesa era originaria la banda The Beatles?", "Liverpool", "Música", "multiple",
     ["Liverpool", "Londres", "Manchester", "Birmingham"]),
    ("¿Qué instrumento de viento es el emblema sonoro del tango rioplatense?", "Bandoneón", "Música", "multiple",
     ["Bandoneón", "Acordeón", "Armónica", "Clarinete"]),
    ("¿Quién compuso la famosa canción argentina 'El amor después del amor'?", "Fito Páez", "Música", "multiple",
     ["Fito Páez", "Charly García", "Andrés Calamaro", "Luis Alberto Spinetta"]),
    ("¿Quién es conocida mundialmente como 'La Reina del Pop'?", "Madonna", "Música", "multiple",
     ["Madonna", "Britney Spears", "Lady Gaga", "Whitney Houston"]),
    ("¿Cuántas cuerdas suele tener una guitarra clásica estándar?", "6 cuerdas", "Música", "multiple",
     ["4 cuerdas", "5 cuerdas", "6 cuerdas", "7 cuerdas"]),
    ("¿Qué banda británica compuso el histórico álbum 'The Dark Side of the Moon'?", "Pink Floyd", "Música", "multiple",
     ["Pink Floyd", "Led Zeppelin", "The Who", "Deep Purple"]),
    ("¿Qué cantante puertorriqueño lanzó el hit global 'Gasolina'?", "Daddy Yankee", "Música", "multiple",
     ["Daddy Yankee", "Don Omar", "Wisin", "Nicky Jam"]),

    # -------------------------------------------------------------
    # 4. HISTORIA Y GEOGRAFÍA (10 preguntas)
    # -------------------------------------------------------------
    ("¿En qué año llegó Cristóbal Colón por primera vez a tierras americanas?", "1492", "Historia y Geografía", "multiple",
     ["1492", "1489", "1500", "1504"]),
    ("¿Cuál es la capital oficial de Canadá?", "Ottawa", "Historia y Geografía", "multiple",
     ["Ottawa", "Toronto", "Montreal", "Vancouver"]),
    ("¿Cuál es el país con mayor superficie territorial del planeta?", "Rusia", "Historia y Geografía", "multiple",
     ["Rusia", "Canadá", "China", "Estados Unidos"]),
    ("¿En qué año finalizó de manera formal la Segunda Guerra Mundial?", "1945", "Historia y Geografía", "multiple",
     ["1943", "1944", "1945", "1948"]),
    ("¿Cuál es el río más caudaloso y extenso del mundo?", "Río Amazonas", "Historia y Geografía", "multiple",
     ["Río Amazonas", "Río Nilo", "Río Misisipi", "Río Danubio"]),
    ("¿Cuál es la capital de Australia?", "Camberra", "Historia y Geografía", "multiple",
     ["Camberra", "Sídney", "Melbourne", "Brisbane"]),
    ("¿Qué civilización precolombina construyó la ciudadela de Machu Picchu?", "Imperio Inca", "Historia y Geografía", "multiple",
     ["Imperio Inca", "Mayas", "Aztecas", "Toltecas"]),
    ("¿En qué año se produjo la caída del Muro de Berlín?", "1989", "Historia y Geografía", "multiple",
     ["1987", "1989", "1991", "1993"]),
    ("¿Cuál es el océano más extenso del planeta Tierra?", "Océano Pacífico", "Historia y Geografía", "multiple",
     ["Océano Pacífico", "Océano Atlántico", "Océano Índico", "Océano Ártico"]),
    ("¿Cuál es la montaña más alta del mundo sobre el nivel del mar?", "Monte Everest", "Historia y Geografía", "multiple",
     ["Monte Everest", "K2", "Kangchenjunga", "Aconcagua"]),

    # -------------------------------------------------------------
    # 5. CIENCIA Y TECNOLOGÍA (10 preguntas)
    # -------------------------------------------------------------
    ("¿Cuál es el elemento químico más abundante en el universo?", "Hidrógeno", "Ciencia y Tecnología", "multiple",
     ["Hidrógeno", "Helio", "Oxígeno", "Carbono"]),
    ("¿A qué temperatura se congela el agua destilada a nivel del mar?", "0 °C", "Ciencia y Tecnología", "multiple",
     ["-4 °C", "0 °C", "4 °C", "32 °C"]),
    ("¿Cuál es el planeta más grande y con más masa de nuestro sistema solar?", "Júpiter", "Ciencia y Tecnología", "multiple",
     ["Júpiter", "Saturno", "Neptuno", "Urano"]),
    ("¿Cuántos huesos conforman el esqueleto humano adulto completamente desarrollado?", "206 huesos", "Ciencia y Tecnología", "multiple",
     ["198 huesos", "206 huesos", "214 huesos", "220 huesos"]),
    ("¿Cuál es la velocidad de la luz en el vacío en cifras redondeadas?", "300.000 km/s", "Ciencia y Tecnología", "multiple",
     ["150.000 km/s", "300.000 km/s", "500.000 km/s", "1.000.000 km/s"]),
    ("¿Qué órgano humano es el encargado de producir la insulina?", "Páncreas", "Ciencia y Tecnología", "multiple",
     ["Páncreas", "Hígado", "Riñón", "Bazo"]),
    ("¿Qué tipo de sangre humana se considera donante universal de glóbulos rojos?", "O negativo", "Ciencia y Tecnología", "multiple",
     ["O negativo", "O positivo", "AB positivo", "A negativo"]),
    ("¿Qué gas representa aproximadamente el 78% del aire que respiramos en la atmósfera?", "Nitrógeno", "Ciencia y Tecnología", "multiple",
     ["Nitrógeno", "Oxígeno", "Dióxido de carbono", "Argón"]),
    ("¿Qué empresa de software fue fundada originalmente por Bill Gates y Paul Allen?", "Microsoft", "Ciencia y Tecnología", "multiple",
     ["Microsoft", "Apple", "IBM", "Intel"]),
    ("¿Cuál es el hueso más largo de todo el cuerpo humano?", "Fémur", "Ciencia y Tecnología", "multiple",
     ["Fémur", "Tibia", "Húmero", "Radio"]),

    # -------------------------------------------------------------
    # 6. CULTURA GENERAL (10 preguntas)
    # -------------------------------------------------------------
    ("¿Quién pintó la mundialmente famosa obra 'La Gioconda' (Mona Lisa)?", "Leonardo da Vinci", "Cultura General", "multiple",
     ["Leonardo da Vinci", "Miguel Ángel", "Rafael", "Sandro Botticelli"]),
    ("¿Cuántos días tiene un año que es bisiesto?", "366 días", "Cultura General", "multiple",
     ["364 días", "365 días", "366 días", "367 días"]),
    ("¿Qué animal ostenta el récord de ser el mamífero más grande de la Tierra?", "Ballena azul", "Cultura General", "multiple",
     ["Ballena azul", "Elefante africano", "Cachalote", "Tiburón ballena"]),
    ("¿Cuántas casillas cuadradas en total componen un tablero de ajedrez?", "64 casillas", "Cultura General", "multiple",
     ["32 casillas", "64 casillas", "81 casillas", "100 casillas"]),
    ("¿Quién es el autor de la celebrada novela 'Don Quijote de la Mancha'?", "Miguel de Cervantes", "Cultura General", "multiple",
     ["Miguel de Cervantes", "Lope de Vega", "Francisco de Quevedo", "Federico García Lorca"]),
    ("¿En qué país asiático se originó originariamente la comida tradicional del sushi?", "Japón", "Cultura General", "multiple",
     ["Japón", "China", "Corea del Sur", "Tailandia"]),
    ("¿Cuántos lados iguales o desiguales tiene un heptágono?", "7 lados", "Cultura General", "multiple",
     ["6 lados", "7 lados", "8 lados", "9 lados"]),
    ("¿Qué escritor colombiano fue galardonado con el Premio Nobel y escribió 'Cien años de soledad'?", "Gabriel García Márquez", "Cultura General", "multiple",
     ["Gabriel García Márquez", "Mario Vargas Llosa", "Julio Cortázar", "Jorge Luis Borges"]),
    ("¿Qué metal noble tiene por símbolo químico 'Au' en la tabla periódica?", "Oro", "Cultura General", "multiple",
     ["Oro", "Plata", "Cobre", "Platino"]),
    ("¿Cuántas patas tiene anatómicamente una araña?", "8 patas", "Cultura General", "multiple",
     ["6 patas", "8 patas", "10 patas", "12 patas"]),
]


def cargar():
    init_db()  # Garantiza que la columna 'opciones' exista en la tabla preguntas
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    agregadas = 0
    saltadas = 0

    for consigna, respuesta, categoria, tipo, opciones in PREGUNTAS_MULTIPLE_CHOICE:
        cursor.execute("SELECT COUNT(*) FROM preguntas WHERE consigna = ?", (consigna,))
        ya_existe = cursor.fetchone()[0] > 0

        if ya_existe:
            saltadas += 1
            continue

        insert_question(consigna, respuesta, categoria, tipo, opciones)
        agregadas += 1

    conn.close()

    print(f"-> Se agregaron {agregadas} preguntas Multiple Choice nuevas distribuidas en las 6 categorías.")
    if saltadas:
        print(f"-> Se saltearon {saltadas} preguntas porque ya figuraban exactamente con la misma consigna.")


if __name__ == "__main__":
    cargar()