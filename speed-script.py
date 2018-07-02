import datetime
import time
import cv2
from collections import deque
import mysql.connector


def connect_to_db(conn_params):
    while True:
        try:
            print "[Info] Connecting to db"
            connection = mysql.connector.connect(buffered=True, **conn_params)
            print "[Info] Connection successful!"
            return connection
        except mysql.connector.errors.InterfaceError:
            print "[Error] Couldn't connect to database. Retrying..."
            sleep(1)

# Datos para la camara
camara = cv2.VideoCapture(0)
time.sleep(0.25)

# Datos para actualizar el frame de referencia
tiempo_frame_referencia = 0
hora_actualizacion_frame = datetime.datetime.now()
ReferenceFrame = None

# Datos para mostrar la imagen de la camara
camara_imagen = False
x1 = 0
x2 = 0
y1 = 0
y2 = 0

# Datos Conexion base de datos
usuario = ""
clave = ""
nombre_base_de_datos = ""

# Datos para guardar en la base de Datos
hora_guardar_movimiento_cola = datetime.datetime.now()

# Se inicializan las variables con el documento externo
archivo = open("ParametrosSensor", 'r')
for line in archivo:
    line = line.replace('\n', ' ')
    elementos = line.split('=')
    if elementos[0] == "tiempo_frame_referencia":
        tiempo_frame_referencia = int(elementos[1])
    elif elementos[0] == "graficos":
        if elementos[1] == "True":
            camara_imagen = True
        else:
            camara_imagen = False
    elif elementos[0] == "x1":
        x1 = int(elementos[1])
    elif elementos[0] == "x2":
        x2 = int(elementos[1])
    elif elementos[0] == "y1":
        y1 = int(elementos[1])
    elif elementos[0] == "y2":
        y2 = int(elementos[1])
    elif elementos[0] == "usuario":
        usuario = elementos[1]
    elif elementos[0] == "clave":
        clave = elementos[1]
    elif elementos[0] == "nombre_base_de_datos":
        nombre_base_de_datos = elementos[1]

CONN_PARAMS = {
  'user': 'ALPR',
  'password': 'PASSALPR',
  'host': 'docker-db',
  'database': 'control_point'
}

# Coneccion con base de datos
connection = connect_to_db(CONN_PARAMS).cursor()

camara_imagen = True
# Loop infinito para registrar movimiento
while True:
    (grabbed, frame) = camara.read()
    texto = "No hay movimiento"
    hay_movimiento = False

    if not grabbed:
        break

    frame = frame[y1:y2, x1:x2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if hora_actualizacion_frame <= datetime.datetime.now():
        ReferenceFrame = gray
        hora_actualizacion_frame += datetime.timedelta(seconds=tiempo_frame_referencia)
        continue

    frameDelta = cv2.absdiff(ReferenceFrame, gray)
    thresh = cv2.threshold(frameDelta, 25, 255, cv2.THRESH_BINARY)[1]

    thresh = cv2.dilate(thresh, None, iterations=2)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in cnts:
        if cv2.contourArea(c) < 500:
            continue
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        texto = "Hay movimiento"
        hay_movimiento = True

    if camara_imagen:
        cv2.putText(frame, "Via: {}".format(texto), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.imshow("Security Feed", frame)
        cv2.imshow("Thresh", thresh)
        cv2.imshow("Frame Delta", frameDelta)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    # Se verifica que paso un segundo desde la ultima vez que se guardo si hay movimiento
    if hora_guardar_movimiento_cola <= datetime.datetime.now():
        if hay_movimiento:
            # Hay movimiento
            # Se guarda de que hubo detencion en la Base de Datos
            cursor.execute("INSERT INTO bus_speed (speed) VALUES (1);")
            print "Guardado: Se detuvo el vehiculo en el tiempo"

        elif not hay_movimiento:
            # No hay movimiento
            # Se guarda de que no hubo detencion en la Base de Datos
            cursor.execute("INSERT INTO bus_speed (speed) VALUES (1);")
            print "Guardado: No se detuvo el vehiculo en el tiempo"

        hora_guardar_movimiento_cola += datetime.timedelta(seconds=1)

# Se corta la conexion con la camara y se destruyen las vistas de esta
camara.release()
cv2.destroyAllWindows()
db.close()