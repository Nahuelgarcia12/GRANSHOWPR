import sqlite3

PREGUNTAS_100 = [
    # -------------------------------------------------------------
    # 1. DEPORTES (17 preguntas)
    # -------------------------------------------------------------
    ("¿Qué selección nacional de fútbol ganó el Mundial de Qatar 2022?", "Argentina", "Deportes"),
    ("¿En qué club europeo disputó Lionel Messi la mayor parte de su carrera profesional?", "FC Barcelona", "Deportes"),
    ("¿Cuántos jugadores por equipo juegan simultáneamente en la cancha en un partido de básquet?", "5", "Deportes"),
    ("¿Quién tiene el récord mundial de velocidad en 100 metros llanos con 9.58 segundos?", "Usain Bolt", "Deportes"),
    ("¿En qué país se disputaron los Juegos Olímpicos del año 2008?", "China (Pekín)", "Deportes"),
    ("¿Qué tenista suizo ganó 20 títulos de Grand Slam y es apodado 'Su Majestad'?", "Roger Federer", "Deportes"),
    ("¿Qué tenista español es conocido como el 'Rey de la Tierra Batida' por sus títulos en Roland Garros?", "Rafael Nadal", "Deportes"),
    ("¿Cuántos puntos otorga un try en el rugby union?", "5 puntos", "Deportes"),
    ("¿Qué piloto de Fórmula 1 comparte con Lewis Hamilton el récord de 7 campeonatos mundiales?", "Michael Schumacher", "Deportes"),
    ("¿En qué equipo de la NBA jugó Emanuel Ginóbili toda su carrera en Estados Unidos?", "San Antonio Spurs", "Deportes"),
    ("¿Quién anotó el famoso gol conocido como 'La Mano de Dios' en el Mundial de 1986?", "Diego Armando Maradona", "Deportes"),
    ("¿De qué color es la tarjeta que expulsa a un jugador de forma directa en el fútbol?", "Roja", "Deportes"),
    ("¿Cuántos hoyos componen una vuelta reglamentaria tradicional en una cancha de golf?", "18 hoyos", "Deportes"),
    ("¿En qué superficie se juega el tradicional torneo de Grand Slam de Wimbledon?", "Césped natural", "Deportes"),
    ("¿Cuál es el estilo de natación que se considera comúnmente el más rápido?", "Crol (o estilo libre)", "Deportes"),
    ("¿Qué selección de fútbol ganó el Mundial de Sudáfrica 2010?", "España", "Deportes"),
    ("¿Cuántos minutos dura oficialmente un tiempo reglamentario en un partido de fútbol sin contar descuentos?", "45 minutos", "Deportes"),

    # -------------------------------------------------------------
    # 2. CINE Y SERIES (17 preguntas)
    # -------------------------------------------------------------
    ("¿Qué director dirigió 'Jurassic Park', 'Tiburón' y 'E.T., el extraterrestre'?", "Steven Spielberg", "Cine y Series"),
    ("¿Qué actor interpretó al excéntrico pirata Jack Sparrow en 'Piratas del Caribe'?", "Johnny Depp", "Cine y Series"),
    ("¿Cómo se llama el villano con armadura oscura y respiración mecánica en 'Star Wars'?", "Darth Vader", "Cine y Series"),
    ("¿Qué película animada de 1995 fue protagonizada por el vaquero Woody y el astronauta Buzz Lightyear?", "Toy Story", "Cine y Series"),
    ("¿Quién interpreta al personaje de Walter White en la serie 'Breaking Bad'?", "Bryan Cranston", "Cine y Series"),
    ("¿Qué actor protagonizó las películas argentinas 'El secreto de sus ojos' y 'Relatos Salvajes'?", "Ricardo Darín", "Cine y Series"),
    ("¿Cómo se llama la pequeña criatura de 'El Señor de los Anillos' obsesionada con 'Mi tesoro'?", "Gollum", "Cine y Series"),
    ("¿En qué cafetería neoyorquina solían reunirse los protagonistas de la comedia 'Friends'?", "Central Perk", "Cine y Series"),
    ("¿Qué criatura gigante de color verde es el álter ego furioso del doctor Bruce Banner en Marvel?", "Hulk", "Cine y Series"),
    ("¿Quién dirigió las películas de ciencia ficción 'Inception', 'Interstellar' y 'Oppenheimer'?", "Christopher Nolan", "Cine y Series"),
    ("¿Qué actor interpretó a Jack Dawson en la galardonada película 'Titanic' de 1997?", "Leonardo DiCaprio", "Cine y Series"),
    ("¿Cómo se llama el reino ficticio gobernado por Mufasa en 'El Rey León'?", "Las Tierras del Reino (Pride Lands)", "Cine y Series"),
    ("¿Qué superhéroe multimillonario de Marvel construye una armadura con un reactor Arc en el pecho?", "Iron Man (Tony Stark)", "Cine y Series"),
    ("¿Cómo se llama la escuela de magia a la que asiste el joven Harry Potter?", "Hogwarts", "Cine y Series"),
    ("¿Qué droide blanco y azul emite pitidos y acompaña a Luke Skywalker en Star Wars?", "R2-D2", "Cine y Series"),
    ("¿Quién compuso la música instrumental de 'Star Wars', 'Indiana Jones' y 'Harry Potter'?", "John Williams", "Cine y Series"),
    ("¿Qué actor dio vida a Neo en la saga de ciencia ficción 'Matrix'?", "Keanu Reeves", "Cine y Series"),

    # -------------------------------------------------------------
    # 3. MÚSICA (16 preguntas)
    # -------------------------------------------------------------
    ("¿Cuál es el álbum musical más vendido de toda la historia a nivel global?", "Thriller (Michael Jackson)", "Música"),
    ("¿Quién es universalmente recordado como 'El Rey del Rock and Roll'?", "Elvis Presley", "Música"),
    ("¿De qué mítica banda británica de rock fue cantante líder Freddie Mercury?", "Queen", "Música"),
    ("¿Cuántas cuerdas suele tener una guitarra clásica o criolla tradicional?", "6 cuerdas", "Música"),
    ("¿Qué cuarteto británico de Liverpool estuvo integrado por Lennon, McCartney, Harrison y Starr?", "The Beatles", "Música"),
    ("¿Qué compositor clásico compuso la Quinta y la Novena Sinfonía habiendo perdido la audición?", "Ludwig van Beethoven", "Música"),
    ("¿Qué trío de rock argentino liderado por Gustavo Cerati compuso el tema 'De música ligera'?", "Soda Stereo", "Música"),
    ("¿Qué músico de rock argentino formó bandas históricas como Sui Generis y Serú Girán?", "Charly García","Música"),
    ("¿En qué década del siglo XX tuvo lugar el histórico festival de música de Woodstock?", "Década de 1960 (1969)", "Música"),
    ("¿Qué instrumento de viento de madera suele dar la nota de referencia para afinar una orquesta?", "El oboe", "Música"),
    ("¿Cuántas teclas en total tiene un piano acústico estándar tradicional?", "88 teclas", "Música"),
    ("¿Qué cantante estadounidense es mundialmente conocida como 'La Reina del Pop'?", "Madonna", "Música"),
    ("¿Quién era el líder, cantante y guitarrista principal de la banda grunge Nirvana?", "Kurt Cobain", "Música"),
    ("¿En qué ciudad estadounidense del sur nació el género musical Jazz a finales del siglo XIX?", "Nueva Orleans", "Música"),
    ("¿Qué instrumento tradicional de fuelles es el emblema sonoro del tango rioplatense?", "El bandoneón", "Música"),
    ("¿Qué banda australiana de hard rock compuso clásicos como 'Highway to Hell' y 'Back in Black'?", "AC/DC", "Música"),

    # -------------------------------------------------------------
    # 4. HISTORIA Y GEOGRAFÍA (17 preguntas)
    # -------------------------------------------------------------
    ("¿En qué año llegó la expedición de Cristóbal Colón a tierras americanas?", "1492", "Historia y Geografía"),
    ("¿En qué año se inició la Revolución Francesa con la toma de la fortaleza de la Bastilla?", "1789", "Historia y Geografía"),
    ("¿En qué año finalizó de manera oficial la Segunda Guerra Mundial?", "1945", "Historia y Geografía"),
    ("¿En qué año cayó el emblemático Muro de Berlín en Alemania?", "1989", "Historia y Geografía"),
    ("¿En qué año se declaró formalmente la Independencia de las Provincias Unidas del Río de la Plata en Tucumán?", "1816", "Historia y Geografía"),
    ("¿Qué prócer militar argentino lideró el Cruce de los Andes para liberar Chile y Perú?", "José de San Martín", "Historia y Geografía"),
    ("¿Cuál es el río más largo y caudaloso del planeta Tierra?", "Río Amazonas", "Historia y Geografía"),
    ("¿Cuál es la cordillera continental más extensa del mundo?", "Cordillera de los Andes", "Historia y Geografía"),
    ("¿Cuál es la montaña más alta de la Tierra sobre el nivel del mar?", "Monte Everest", "Historia y Geografía"),
    ("¿Cuál es la capital oficial de Australia?", "Camberra", "Historia y Geografía"),
    ("¿Cuál es la capital oficial de Canadá?", "Ottawa", "Historia y Geografía"),
    ("¿Cuál es la capital de Brasil?", "Brasilia", "Historia y Geografía"),
    ("¿Cuál es el país más extenso del mundo en superficie continental?", "Rusia", "Historia y Geografía"),
    ("¿Cuál es el estado soberano más pequeño del mundo, situado en el corazón de Roma?", "Ciudad del Vaticano", "Historia y Geografía"),
    ("¿Qué civilización precolombina levantó la ciudadela de piedra de Machu Picchu?", "Imperio Inca", "Historia y Geografía"),
    ("¿En qué país actual se encuentran las famosas pirámides de Keops, Kefrén y Micerino?", "Egipto", "Historia y Geografía"),
    ("¿Cuál es el océano más grande del mundo en superficie y volumen?", "Océano Pacífico", "Historia y Geografía"),

    # -------------------------------------------------------------
    # 5. CIENCIA Y TECNOLOGÍA (17 preguntas)
    # -------------------------------------------------------------
    ("¿Cuál es el elemento químico más ligero y abundante del universo observable?", "Hidrógeno (H)", "Ciencia y Tecnología"),
    ("¿Qué planeta se encuentra más próximo al Sol en el sistema solar?", "Mercurio", "Ciencia y Tecnología"),
    ("¿Cuál es el planeta más grande y masivo del sistema solar?", "Júpiter", "Ciencia y Tecnología"),
    ("¿Quién postuló la Teoría de la Relatividad General y Especial a principios del siglo XX?", "Albert Einstein", "Ciencia y Tecnología"),
    ("¿Qué científico británico formuló la Ley de Gravitación Universal tras estudiar la caída de los cuerpos?", "Isaac Newton", "Ciencia y Tecnología"),
    ("¿Quién sentó las bases de la biología moderna con su teoría sobre el origen de las especies por selección natural?", "Charles Darwin", "Ciencia y Tecnología"),
    ("¿Cuál es la velocidad aproximada a la que viaja la luz en el vacío expresada en km/s?", "300.000 km/s", "Ciencia y Tecnología"),
    ("¿Qué órgano central del sistema circulatorio humano impulsa la sangre a los tejidos?", "El corazón", "Ciencia y Tecnología"),
    ("¿Cuál es la macromolécula que almacena las instrucciones genéticas de la vida celular?", "ADN", "Ciencia y Tecnología"),
    ("¿Qué gas indispensable liberan los vegetales mediante el proceso diurno de la fotosíntesis?", "Oxígeno", "Ciencia y Tecnología"),
    ("¿A qué temperatura hierve el agua destilada a nivel del mar en la escala Celsius?", "100 °C", "Ciencia y Tecnología"),
    ("¿A qué temperatura se congela el agua pura a presión atmosférica estándar en grados Celsius?", "0 °C", "Ciencia y Tecnología"),
    ("¿Cuántos huesos componen el esqueleto de un cuerpo humano adulto completamente desarrollado?", "206 huesos", "Ciencia y Tecnología"),
    ("¿Qué empresa de software fue fundada originalmente por Bill Gates y Paul Allen?", "Microsoft", "Ciencia y Tecnología"),
    ("¿Qué compañía multinacional de tecnología creó los teléfonos iPhone y las computadoras Mac?", "Apple", "Ciencia y Tecnología"),
    ("¿Qué famoso motor de búsqueda en Internet fue creado por Larry Page y Sergey Brin?", "Google", "Ciencia y Tecnología"),
    ("¿Qué tipo de sangre humana es clasificada como donante universal de glóbulos rojos?", "O negativo (O-)", "Ciencia y Tecnología"),

    # -------------------------------------------------------------
    # 6. CULTURA GENERAL (16 preguntas)
    # -------------------------------------------------------------
    ("¿Cuántos días tiene un año que es bisiesto?", "366 días", "Cultura General"),
    ("¿Cuántos meses del calendario gregoriano poseen exactamente 31 días?", "7 meses", "Cultura General"),
    ("¿Quién pintó la célebre obra renacentista conocida como 'La Gioconda' o Mona Lisa?", "Leonardo da Vinci", "Cultura General"),
    ("¿Qué célebre artista pintó la bóveda de la Capilla Sixtina en el Vaticano?", "Miguel Ángel", "Cultura General"),
    ("¿Quién es el autor de la célebre obra de la literatura española 'Don Quijote de la Mancha'?", "Miguel de Cervantes", "Cultura General"),
    ("¿Qué dramaturgo inglés escribió las obras teatrales 'Romeo y Julieta' y 'Hamlet'?", "William Shakespeare", "Cultura General"),
    ("¿Qué autor colombiano ganó el Nobel de Literatura y escribió 'Cien años de soledad'?", "Gabriel García Márquez", "Cultura General"),
    ("¿Qué felino terrestre ostenta el récord de mayor velocidad en distancias cortas?", "El guepardo (o chita)", "Cultura General"),
    ("¿Cuál es el mamífero y animal más grande del planeta Tierra?", "La ballena azul", "Cultura General"),
    ("¿En qué país asiático se originó tradicionalmente el plato culinario conocido como sushi?", "Japón", "Cultura General"),
    ("¿Cuántos colores componen la descomposición clásica del arcoíris descrita por Newton?", "7 colores", "Cultura General"),
    ("¿Cuál es la divisa oficial compartida por la gran mayoría de los países de la Unión Europea?", "El Euro (€)", "Cultura General"),
    ("¿Qué metal noble y precioso tiene como símbolo químico las letras 'Au'?", "Oro", "Cultura General"),
    ("¿Qué filósofo griego fue maestro de Platón y fue condenado a morir bebiendo cicuta?", "Sócrates", "Cultura General"),
    ("¿Sobre cuántas casillas cuadradas alternadas de dos colores se disputa el juego del ajedrez?", "64 casillas", "Cultura General"),
    ("¿Qué animal mitológico egipcio posee cuerpo de león y cabeza humana?", "La Esfinge", "Cultura General")
]

def poblar_100_preguntas():
    conn = sqlite3.connect("trivia.db")
    cursor = conn.cursor()

    # Reiniciar la tabla para que no queden datos de prueba
    cursor.execute("DROP TABLE IF EXISTS preguntas")
    cursor.execute("""
        CREATE TABLE preguntas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consigna TEXT NOT NULL,
            respuesta_correcta TEXT NOT NULL,
            categoria TEXT NOT NULL,
            tipo TEXT DEFAULT 'abierta'
        )
    """)

    for consigna, resp, cat in PREGUNTAS_100:
        cursor.execute("""INSERT INTO preguntas (consigna, respuesta_correcta, categoria, tipo)VALUES (?, ?, ?, 'abierta')
        """, (consigna, resp, cat))

    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM preguntas")
    total = cursor.fetchone()[0]
    conn.close()

    print(f"Base de datos 'trivia.db' lista y limpia con {total} preguntas reales y variadas.")

if __name__ == "__main__":
    poblar_100_preguntas()