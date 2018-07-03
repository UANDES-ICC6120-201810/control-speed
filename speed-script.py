from datetime import datetime, timedelta
import cv2
import mysql.connector

PARAM_FILENAME = 'ParametrosSensor'

def main():
    params_dict = parse_param_file(PARAM_FILENAME)

    camera = cv2.VideoCapture(params_dict['camera_url'])

    reference_frame = get_current_frame(camera)

    reference_frame_time_limit = datetime.now()
    movement_check_time_limit = reference_frame_time_limit + timedelta(seconds=params_dict['seconds_between_frames'])

    while True:
        should_check_for_movement = time_limit_expired(movement_check_time_limit)

        if should_check_for_movement:
            current_frame = get_current_frame(camera)

            movement_detected = detect_movement(reference_frame, current_frame)

            if movement_detected:
                post_movement_event_to_db(params_dict)

            reference_frame = get_current_frame(camera)
            reference_frame_time_limit = movement_check_time_limit + timedelta(seconds=params_dict['seconds_between_motion_detection'])
            movement_check_time_limit = reference_frame_time_limit + timedelta(seconds=params_dict['seconds_between_frames'])

    camera.release()

def parse_param_file(param_filename):
    params_dict = {}

    params_file = open(param_filename, 'r')
    for line_number, line in enumerate(params_file):

        if should_ignore_line(line):
            continue

        try:
            key, value = line.strip().split('=')
            params_dict[key] = safe_cast(value)
            
        except ValueError:
            print "Invalid row {0} in file {1}".format(line_number, param_filename)
            continue

    return params_dict

def should_ignore_line(line):
    line = line.strip()
    if len(line) < 3:  # 3 because the min expression is a=b
        return True
    elif line[0] == '#':
        return True

    return False

def safe_cast(value):
    try:
        return int(value)
    except ValueError:
        pass
    if value == 'True':
        return True
    elif value == 'False':
        return False
    return value

def get_current_frame(camera):
    grabbed = False

    while not grabbed:
        grabbed, current_frame = camera.read()

    current_frame = cut_camera_frame(current_frame, params_dict)

    current_gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    current_blurred_frame = cv2.GaussianBlur(gray, (21, 21), 0)

    return current_blurred_frame

def cut_camera_frame(frame, params_dict):
    try:
        frame = frame[
            params_dict['camera_top_margin_px']:params_dict['camera_bottom_margin_px'],
            params_dict['camera_left_margin_px']:params_dict['camera_right_margin_px']
        ]
    except KeyError as error:
        print "[Error] Missing '{0}' parameter in parameters file.".format(error.args[0])
        exit(1)

    return frame

def detect_movement(reference_frame, frame):
    contours = get_frame_contours(reference_frame, current_frame)

    for contour in contours:
        if cv2.contourArea(contour) >= 500:
            return True

    return False

def get_frame_contours(reference_frame, frame):
    frame_delta = cv2.absdiff(reference_frame, frame)
    frame_thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    frame_dilate = cv2.dilate(frame_thresh, None, iterations=2)

    contours, _ = cv2.findContours(frame_dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    return contours

def post_movement_event_to_db(params_dict):
    max_post_tries = params_dict['max_post_tries']

    for _ in range(max_post_tries):
        connection = connect_to_db(params_dict)
        post_cursor = connection.cursor()

        post_cursor.execute("INSERT INTO bus_speed (speed) VALUES (1);")
        connection.commit()
        print "Guardado: Se detuvo el vehiculo en el tiempo"

        connection.close()

def connect_to_db(params_dict):
    while True:
        try:
            print "[Info] Connecting to db"
            connection = mysql.connector.connect(buffered=True,
                                                 user=params_dict['db_user'],
                                                 password=params_dict['db_password'],
                                                 database=params_dict['db_name'],
                                                 host=params_dict['db_host'])
            print "[Info] Connection successful!"
            return connection
        except mysql.connector.errors.InterfaceError:
            print "[Error] Couldn't connect to database. Retrying..."
            sleep(1)
        except KeyError as error:
            print "[Error] Missing '{0}' parameter in parameters file.".format(error.args[0])
            exit(1)

def time_limit_expired(time_limit):
    return time_limit <= datetime.now()

if __name__ == '__main__':
    main()
