import mysql.connector

def get_db():
    try:
        connection = mysql.connector.connect(
            host="192.168.14.3",
            user="DEV_PPV",
            password="DetMatchPPV",
            database="PetMatch"
        )
        return connection
    except mysql.connector.Error as e:
        print(f"Error al conectar con la base de datos: {e}")
        return None
