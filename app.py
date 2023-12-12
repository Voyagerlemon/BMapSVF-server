"""
Author: xuhy xuhaiyangw@163.com
Date: 2022-07-22 11:20:02
LastEditors: xuhy xuhaiyangw@163.com
LastEditTime: 2022-07-25 17:34:31
FilePath: app.py
Description: BMapSVF API
"""
import os
import cv2
import json
import csv
import time
import base64
import socket
import pymysql
import requests
import datetime
import zipfile
import contextlib
from PIL import Image
import urllib.request
from tqdm import tqdm
from io import BytesIO
import numpy as np
from flask_cors import CORS
from datetime import timedelta
from dbutils.pooled_db import PooledDB
from equire2fisheye512 import equire2fisheye
from generate_token import generate_token, certify_token
from panorama_fisheye import panorama_fisheye
from flask_socketio import SocketIO, emit, send
from calculate_fisheye import calculate_single_fisheye
from flask import Flask, request, jsonify, send_from_directory
from read_panorama import real_time_segmentation, seg_result_img


app = Flask(__name__)

# Configuring session Keys
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=12)
app.config['JSON_AS_ASCII'] = False
# app.config['SESSION_TYPE'] = "redis"    # The session type is redis
# app.config['SESSION_PERMANENT'] = True  # If set to True, closing the browser session is invalid

socketio = SocketIO()
socketio.init_app(app, cors_allowed_origins='*')
CORS(app)

cur_path = os.path.abspath(os.path.dirname(__file__))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Define error handling function
# @app.errorhandler(Exception)
# def handle_error(e):
#     error_message = str(e)
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         s.connect(("127.0.0.1", 5000))
#         s.sendall(error_message.encode("utf-8"))
#     # Return error response
#     return jsonify({"error": error_message})

@app.route('/')
def index():
    return '<h2>Welcome to the BMapSVF server!</h2>'

@socketio.on('message')
def handle_message(message):
    message = urllib.parse.unquote(message)
    print(message)
    send(message, broadcast=True)


# ----------------------------------------------------------------------------------#
# An exception occurs when the connection or disconnection occurs with the server
# ----------------------------------------------------------------------------------#
@socketio.on('connect', namespace='/save')
def save_connect():
    print("Client connected")


@socketio.on('disconnect', namespace='/save')
def save_disconnect():
    print('Client disconnected')

@socketio.on_error('/save')
def error_handler_chat(e):
    print('An error has occurred: ' + str(e))

# ------------------------------------------#
# Websocket Indicates the login interface
# ------------------------------------------#
@socketio.on("login")
def login(get_data):
    username = get_data.get("username")
    password = get_data.get("password")
    if username == "admin" and password == "gis5566":
        token = generate_token(username)
        if certify_token(username, token):
            socketio.emit("loginSuccess", {"status": 200, "token":token, "msg": "Login successful"}, broadcast=True)
        else:
            return
    else:
        socketio.emit("loginError", {"status": 400, "msg": "The account or password is incorrect"}, broadcast=True)
    return token

# -------------------------------------------------------------------------------------#
# Define a context manager that automatically opens and closes database connections
# -------------------------------------------------------------------------------------#
@contextlib.contextmanager
def mysql(host='127.0.0.1', user='root', password='gis5566&', port=3306, db='panorama'):
    conn = pymysql.connect(host=host, port=port, user=user,
                           password=password, db=db)
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        conn.commit()
        cursor.close()
        conn.close()

# -----------------------------------------------POST---------------------------------------------------------#

# ----------------------------------------------------#
# Websocket Interface for processing Baidu Panoramas
# ----------------------------------------------------#
@socketio.on("postSavePanorama")
def save_panorama(get_data):
    try:
        time_start = time.time()
        total_cost = 0
        table = "bmapsvf_test"
        srcPath = get_data.get("srcPath")
        panoid = get_data.get("panoid")
        date = get_data.get("date")
        lng = get_data.get("lng")
        lat = get_data.get("lat")
        descr = get_data.get("description").encode('utf-8').decode('utf-8')
        result = urllib.request.urlopen(srcPath)
        panorama = result.read()

        # Converts binary data into image objects
        img_panorama = Image.open(BytesIO(panorama))
        img_panorama.save(cur_path + "/img_panorama/panorama_00/once.png", "PNG")
        img_fisheye = equire2fisheye(cur_path + "/img_panorama/panorama_00/once.png", 0)

        output_panorama = BytesIO()
        img_fisheye[0].save(output_panorama, format='PNG')
        fisheye = output_panorama.getvalue()

        print('-----Semantic segmentation begins-----')
        socketio.emit("getReadSegInfo", {"msg": "Semantic segmentation is underway!"}, broadcast=True)
        seg_result = real_time_segmentation(cur_path)
        total_cost = seg_result[0]
        print("total time:", f"{total_cost}" + "s")
        socketio.emit("getReadPanorama",
                      {"msg": f"Semantic segmentation is complete, and takes {total_cost:.2f} s. Calculating SVF!",
                       "total_cost": total_cost}, broadcast=True)

        img = cv2.imread(seg_result[1], 1)
        retval, buffer = cv2.imencode('.png', img)
        panorama_seg = np.array(buffer).tobytes()

        print('-----Start calculating SVF-----')
        img_seg_fisheye = equire2fisheye(seg_result[2], 1)
        output_seg_fisheye = BytesIO()
        img_seg_fisheye[0].save(output_seg_fisheye, format='PNG')
        fisheye_seg = output_seg_fisheye.getvalue()
        svf = img_seg_fisheye[1]

        socketio.emit("getCalculateSVF", {"msg": "SVF calculation is complete!", "svf": svf}, broadcast=True)

        with mysql() as cursor:
            cursor.execute(
                "INSERT INTO {}(panoid, date, lng, lat, description, panorama, fisheye, panorama_seg, fisheye_seg, svf) "
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(
                    table),
                (panoid, date, lng, lat, descr, panorama, fisheye, panorama_seg, fisheye_seg, svf))
            print('-----BSV and related information are successfully stored in the database-----')
    except Exception as e:
        socketio.emit("postSaveError", str(e))
    socketio.emit("getSuccessPanorama", {"msg": "Data storage successfully!"}, broadcast=True)

# --------------------------#
# Http Sends a csv file
# --------------------------#
@app.route('/upload', methods=['POST'], strict_slashes=False)
def upload():
    try:
        table = "bmapsvf_transform"
        time_stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        file_csv = request.files['file']
        file_csv.save(cur_path + f"/csv/file_{time_stamp}.csv")
        print('-----The csv file is uploaded successfully. Procedure-----')
        csv_results = []
        # Service address
        host = "https://api.map.baidu.com"
        uri = "/geoconv/v1/"
        aks = ["BrlC46ogjvmEkblNNsauxtjmgKjHBiqN", "uYPVx8FpGoILUNAkM9WGCvFb1t5tQAuH", "h5GlIkW5aT6ZVyESoOtaz5C8KCPpcCLE",
              "YniOI8mkAeMNRPNR4DkFu5LQP9ArmWGn", "YeOWIMkFXGT8k6LIYi6l5eGYEYpnS9gr", "qvIqQKAADKsPFqmxR6T0xP6EtKFT6TjQ",
              "5NLRP7yso7RyZWiSkERyl8ZmPVrOEDRH", "2rP0A4BSKwhFnWnQAvswGIUISoIHRtTU"]
        ak = "BrlC46ogjvmEkblNNsauxtjmgKjHBiqN"
        with open(cur_path + f"/csv/file_{time_stamp}.csv", encoding='utf-8', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            total = 0
            for row in reader:
                total += 1
                wgs84_lng = float(row["lng"])
                wgs84_lat = float(row["lat"])
                params_location = {
                    "coords": row["lng"] + ',' + row["lat"],
                    "from": "1",
                    "to": "5",
                    "ak": ak,
                }
                response = requests.get(url=host + uri, params=params_location)
                if response:
                    result_json = response.json()
                    result_arr = result_json["result"]
                    for result in result_arr:
                        bd09_lng = result['x']
                        bd09_lat = result['y']
                        with mysql() as cursor:
                            cursor.execute(
                                "INSERT INTO {}(bd09_lng, bd09_lat, wgs84_lng, wgs84_lat) "
                                "VALUES(%s, %s, %s, %s)".format(
                                    table),
                                (bd09_lng, bd09_lat, wgs84_lng, wgs84_lat))
                        row_result = {"lng": bd09_lng, "lat": bd09_lat}
                        csv_results.append(row_result)
    except Exception as e:
        socketio.emit("postUploadError", str(e))
    return jsonify({"status": 200, "msg": f"Csv file uploaded successfully, a total of {total} point(s) were loaded!", "csvResults": csv_results})

# ------------------------------------------------------------------------------#
# Websocket processes the Baidu Panorama interface obtained through csv file
# ------------------------------------------------------------------------------#
@socketio.on("postCsvPanoramas")
def csv_panorama(get_data):
    table = "bmapsvf_study"
    try:
        for item in get_data:
            srcPath = item["srcPath"]
            panoid = item["panoid"]
            date = item["date"]
            lng = item["lng"]
            lat = item["lat"]
            descr = item["description"].encode('utf-8').decode('utf-8')
            result = urllib.request.urlopen(srcPath)
            panorama = result.read()

            img_panorama = Image.open(BytesIO(panorama))
            img_panorama.save(cur_path + "/img_panorama/panorama_00/once.png", "PNG")
            img_fisheye = equire2fisheye(cur_path + "/img_panorama/panorama_00/once.png", 0)

            output_panorama = BytesIO()
            img_fisheye[0].save(output_panorama, format='PNG')
            fisheye = output_panorama.getvalue()

            print('-----Semantic segmentation begins-----')
            socketio.emit("getReadSegInfo", {"msg": f"{panoid} point is currently undergoing semantic segmentation!"},
                          broadcast=True)
            seg_result = real_time_segmentation(cur_path)
            total_cost = seg_result[0]
            print("total time:", f"{total_cost}" + "s")
            socketio.emit("getReadPanorama",
                          {
                              "msg": f"Semantic segmentation of {panoid} point has been complete and it took {total_cost:.2f}s. Calculating the SVF!",
                              "total_cost": total_cost}, broadcast=True)

            img = cv2.imread(seg_result[1], 1)
            retval, buffer = cv2.imencode('.png', img)
            panorama_seg = np.array(buffer).tobytes()

            print('-----Start calculating SVF-----')
            img_seg_fisheye = equire2fisheye(seg_result[2], 1)
            output_seg_fisheye = BytesIO()
            img_seg_fisheye[0].save(output_seg_fisheye, format='PNG')
            fisheye_seg = output_seg_fisheye.getvalue()
            svf = img_seg_fisheye[1]

            socketio.emit("getCalculateSVF",
                          {"msg": f"The SVF calculation of {panoid} point has been completed!", "svf": svf},
                          broadcast=True)

            with mysql() as cursor:
                cursor.execute(
                    "INSERT INTO {}(panoid, date, lng, lat, description, panorama, fisheye, panorama_seg, fisheye_seg, svf) "
                    "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(
                        table),
                    (panoid, date, lng, lat, descr, panorama, fisheye, panorama_seg, fisheye_seg, svf))
                print('-----BSV and related information are successfully stored in the database-----')
    except Exception as e:
        socketio.emit("postCsvError", str(e))
    socketio.emit("getSuccessPanorama", {"msg": "All data has been stored successfully!"}, broadcast=True)

# ------------------------------#
# Websocket: WGS84-->BD09
# ------------------------------#
@socketio.on("postTransformWGSCoordinate")
def transform_wgs_coordinate(get_data):
    try:
        lng = get_data['lng']
        lat = get_data['lat']
        host = "https://api.map.baidu.com"
        uri = "/geoconv/v1/"
        ak = "BrlC46ogjvmEkblNNsauxtjmgKjHBiqN"

        params_location = {
            "coords": lng + ',' + lat,
            "from": "1",
            "to": "5",
            "ak": ak,
        }
        response = requests.get(url=host + uri, params=params_location)
        if response:
            result_json = response.json()
            result_arr = result_json["result"]
            for result in result_arr:
                bd09_lng = result['x']
                bd09_lat = result['y']
                row_result = {"lng": bd09_lng, "lat": bd09_lat}
    except Exception as e:
        socketio.emit("postLocationError", str(e))
    socketio.emit("getBD09Coordinate", {"row_result":  row_result}, broadcast=True)

# -----------------------------------------------GET-----------------------------------------------------------#

# ----------------------------------------------------------------------------------------------------#
# Websocket Interface for obtaining the panorama processing result of Baidu Fuhua Road(sample data)
# ----------------------------------------------------------------------------------------------------#
@socketio.on("getPanoramaResults")
def read_panorama(get_data):
    resquest_info = get_data.encode('utf-8').decode('utf-8')
    print(resquest_info)
    with mysql() as cursor:
        cursor.execute("SELECT panoid, lng, lat, fisheye, fisheye_seg, svf FROM bmapsvf_fuhualu")
        result = cursor.fetchall()

    panorama_results = []
    for row in result:
        panoid = row[0]
        lng = row[1]
        lat = row[2]
        fisheye_pro = base64.b64encode(row[3])
        fisheye = fisheye_pro.decode("utf-8")
        fisheye_seg_pro = base64.b64encode(row[4])
        fisheye_seg = fisheye_seg_pro.decode("utf-8")
        svf = row[5]
        row_result = {"panoid": panoid, "lng": lng, "lat": lat, "fisheye": fisheye, "fisheye_seg": fisheye_seg, "svf": svf}
        panorama_results.append(row_result)
    socketio.emit("postPanoramaResults", {"panoramaResults": panorama_results}, broadcast=True)

# --------------------------------------------------------------------------------#
# Websocket Interface for obtaining Qinhuai Baidu Panorama processing results
# --------------------------------------------------------------------------------#
@socketio.on("getCsvPanoramaResults")
def read_csv_panorama(get_data):
    resquest_info = get_data.encode('utf-8').decode('utf-8')
    print(resquest_info)
    with mysql() as cursor:
        cursor.execute("SELECT panoid, lng, lat, fisheye, fisheye_seg, svf FROM bmapsvf_qinhuai WHERE id <=300")
        result = cursor.fetchall()

    panorama_results = []
    for row in result:
        panoid = row[0]
        lng = row[1]
        lat = row[2]
        fisheye_pro = base64.b64encode(row[3])
        fisheye = fisheye_pro.decode("utf-8")
        fisheye_seg_pro = base64.b64encode(row[4])
        fisheye_seg = fisheye_seg_pro.decode("utf-8")
        svf = row[5]
        row_result = {"panoid": panoid, "lng": lng, "lat": lat, "fisheye": fisheye, "fisheye_seg": fisheye_seg, "svf": svf}
        panorama_results.append(row_result)
    socketio.emit("postCsvPanoramaResults", {"panoramaResults": panorama_results}, broadcast=True)

# ---------------------------------------------------------------------------------------#
# Websocket Interface for obtaining SVF results of Baidu Panorama in Qinhuai District
# ---------------------------------------------------------------------------------------#
@socketio.on("getCsvSVFResults")
def read_csv_svf(get_data):
    resquest_info = get_data.encode('utf-8').decode('utf-8')
    print(resquest_info)
    with mysql() as cursor:
        cursor.execute("SELECT lng, lat, svf, fisheye, fisheye_seg FROM bmapsvf_qinhuai")
        result = cursor.fetchall()

    fisheye_pro = base64.b64encode(result[422][3])
    fisheye = fisheye_pro.decode("utf-8")
    fisheye_seg_pro = base64.b64encode(result[422][4])
    fisheye_seg = fisheye_seg_pro.decode("utf-8")
    fisheye_results = []
    fisheye_results.append({"fisheye": fisheye, "fisheye_seg": fisheye_seg})
    svf_results = []
    for row in result:
        lng = row[0]
        lat = row[1]
        svf = row[2]
        row_result = {"lng": lng, "lat": lat, "svf": svf}
        svf_results.append(row_result)
    socketio.emit("postCsvSVFResults", {"svfResults": svf_results, "fisheyeResults": fisheye_results}, broadcast=True)

# ------------------------------------------------#
# Websocket obtains the Fuhua data and saves it
# ------------------------------------------------#
@socketio.on("getFuhuaPanoramaResults")
def read_fuhua_panorama(get_data):
    print('-----%s-----' % get_data)
    table_name = 'bmapsvf_fuhualu'

    # Create a temporary directory to store the folders and files you want to export
    temp_dir = 'temp'
    os.makedirs(temp_dir, exist_ok=True)

    # Create four folders to store the data
    folders = ['panorama', 'panorama_seg', 'fisheye', 'fisheye_seg']
    for folder in folders:
        folder_path = os.path.join(temp_dir, folder)
        os.makedirs(folder_path, exist_ok=True)

    # Get SVF field name --> Create csv file
    with mysql() as cursor:
        cursor.execute("DESC %s" % table_name)
        field_names = [row[0] for row in cursor.fetchall()]
        field_names.remove("panorama")
        field_names.remove("panorama_seg")
        field_names.remove("fisheye")
        field_names.remove("fisheye_seg")

    with mysql() as cursor:
        cursor.execute("SELECT id, panoid, date, lng, lat, description, svf FROM %s" % table_name)
        result = cursor.fetchall()

    file_name = "%s.csv" % table_name
    file_path = os.path.join(temp_dir, file_name)

    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(field_names)
        for row in result:
            writer.writerow(row)

    with mysql() as cursor:
        cursor.execute("SELECT id, lng, lat, fisheye, fisheye_seg, panorama, panorama_seg FROM %s" % table_name)
        result = cursor.fetchall()

    panorama_results = []
    for row in result:
        pan_id = str(row[0])
        pan_lng = str(row[1])
        pan_lat = str(row[2])
        pan_fisheye = row[3]
        pan_fisheye_seg = row[4]
        pan_picture = row[5]
        pan_picture_seg = row[6]

        folder_panorama_name = folders[0]
        folder_panorama_path = os.path.join(temp_dir, folder_panorama_name)
        save_panorama_name = pan_id + "_" + pan_lng + "_" + pan_lat + "_" + "panorama" + ".png"
        file_panorama_path = os.path.join(folder_panorama_path, save_panorama_name)
        f_panorama = open(file_panorama_path, 'wb')
        f_panorama.write(pan_picture)
        f_panorama.close()

        folder_panorama_seg_name = folders[1]
        folder_panorama_seg_path = os.path.join(temp_dir, folder_panorama_seg_name)
        save_panorama_seg_name = pan_id + "_" + pan_lng + "_" + pan_lat + "_" + "panorama_seg" + ".png"
        file_panorama_seg_path = os.path.join(folder_panorama_seg_path, save_panorama_seg_name)
        f_panorama_seg = open(file_panorama_seg_path, 'wb')
        f_panorama_seg.write(pan_picture_seg)
        f_panorama_seg.close()

        folder_fisheye_name = folders[2]
        folder_fisheye_path = os.path.join(temp_dir, folder_fisheye_name)
        save_fisheye_name = pan_id + "_" + pan_lng + "_" + pan_lat + "_" + "fisheye" + ".png"
        file_fisheye_path = os.path.join(folder_fisheye_path, save_fisheye_name)
        f_fisheye = open(file_fisheye_path, 'wb')
        f_fisheye.write(pan_fisheye)
        f_fisheye.close()

        folder_fisheye_seg_name = folders[3]
        folder_fisheye_seg_path = os.path.join(temp_dir, folder_fisheye_seg_name)
        save_fisheye_seg_name = pan_id + "_" + pan_lng + "_" + pan_lat + "_" + "fisheye_seg" + ".png"
        file_fisheye_seg_path = os.path.join(folder_fisheye_seg_path, save_fisheye_seg_name)
        f_fisheye_seg = open(file_fisheye_seg_path, 'wb')
        f_fisheye_seg.write(pan_fisheye_seg)
        f_fisheye_seg.close()

    zip_file_path = BytesIO()
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add folders and files from the temporary directory to the zip zip package
        for  root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, temp_dir))
    print('-----All data is saved successfully------')
    socketio.emit("postFuhuaPanoramaResults", {"status": 200, "name": table_name, "data": zip_file_path.getvalue()}, broadcast=True)
    # Deleting a temporary directory
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            os.rmdir(dir_path)

# ------------------------------------------------------#
# Websocket obtains Qinhuai region data and saves it
# ------------------------------------------------------#
@socketio.on("getQinhuaiPanoramaResults")
def read_qinhuai_panorama(get_data):
    print('-----%s-----' % get_data)
    table_name = 'bmapsvf_qinhuai'

    temp_dir = 'temp'
    os.makedirs(temp_dir, exist_ok=True)

    folders = ['panorama', 'panorama_seg', 'fisheye', 'fisheye_seg']
    for folder in folders:
        folder_path = os.path.join(temp_dir, folder)
        os.makedirs(folder_path, exist_ok=True)

    with mysql() as cursor:
        cursor.execute("DESC %s" % table_name)
        field_names = [row[0] for row in cursor.fetchall()]
        field_names.remove("panorama")
        field_names.remove("panorama_seg")
        field_names.remove("fisheye")
        field_names.remove("fisheye_seg")

    with mysql() as cursor:
        cursor.execute("SELECT id, panoid, date, lng, lat, description, svf FROM %s" % table_name)
        result = cursor.fetchall()

    file_name = "%s.csv" % table_name
    file_path = os.path.join(temp_dir, file_name)

    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(field_names)
        for row in result:
            writer.writerow(row)

    with mysql() as cursor:
        cursor.execute("SELECT id, lng, lat, fisheye, fisheye_seg, panorama, panorama_seg FROM %s" % table_name)
        result = cursor.fetchall()

    panorama_results = []
    for row in result:
        pan_id = str(row[0])
        pan_lng = str(row[1])
        pan_lat = str(row[2])
        pan_fisheye = row[3]
        pan_fisheye_seg = row[4]
        pan_picture = row[5]
        pan_picture_seg = row[6]

        folder_panorama_name = folders[0]
        folder_panorama_path = os.path.join(temp_dir, folder_panorama_name)
        save_panorama_name = pan_id + "_" + pan_lng + "_" + pan_lat + "_" + "panorama" + ".png"
        file_panorama_path = os.path.join(folder_panorama_path, save_panorama_name)
        f_panorama = open(file_panorama_path, 'wb')
        f_panorama.write(pan_picture)
        f_panorama.close()

        folder_panorama_seg_name = folders[1]
        folder_panorama_seg_path = os.path.join(temp_dir, folder_panorama_seg_name)
        save_panorama_seg_name = pan_id + "_" + pan_lng + "_" + pan_lat + "_" + "panorama_seg" + ".png"
        file_panorama_seg_path = os.path.join(folder_panorama_seg_path, save_panorama_seg_name)
        f_panorama_seg = open(file_panorama_seg_path, 'wb')
        f_panorama_seg.write(pan_picture_seg)
        f_panorama_seg.close()

        folder_fisheye_name = folders[2]
        folder_fisheye_path = os.path.join(temp_dir, folder_fisheye_name)
        save_fisheye_name = pan_id + "_" + pan_lng + "_" + pan_lat + "_" + "fisheye" + ".png"
        file_fisheye_path = os.path.join(folder_fisheye_path, save_fisheye_name)
        f_fisheye = open(file_fisheye_path, 'wb')
        f_fisheye.write(pan_fisheye)
        f_fisheye.close()

        folder_fisheye_seg_name = folders[3]
        folder_fisheye_seg_path = os.path.join(temp_dir, folder_fisheye_seg_name)
        save_fisheye_seg_name = pan_id + "_" + pan_lng + "_" + pan_lat + "_" + "fisheye_seg" + ".png"
        file_fisheye_seg_path = os.path.join(folder_fisheye_seg_path, save_fisheye_seg_name)
        f_fisheye_seg = open(file_fisheye_seg_path, 'wb')
        f_fisheye_seg.write(pan_fisheye_seg)
        f_fisheye_seg.close()

    zip_file_path = BytesIO()
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for  root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, temp_dir))

    print('-----All data is saved successfully------')
    socketio.emit("postQinhuaiPanoramaResults", {"status": 200, "name": table_name, "data": zip_file_path.getvalue()}, broadcast=True)
    # Deleting a temporary directory
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            os.rmdir(dir_path)

# -------------------------------------------------------------------------------#
# Websocket obtained part of Qinhuai district data to verify the 3D simulation
# -------------------------------------------------------------------------------#
@socketio.on("getQinhuaiLessResults")
def read_qinhuai_less(get_data):
    print('-----%s-----' % get_data)
    table_name = 'bmapsvf_qinhuai'
    with mysql() as cursor:
        cursor.execute("SELECT id, lng, lat FROM %s WHERE id>=275 && id<=430" % table_name)
        result = cursor.fetchall()

    id_results = []
    for row in result:
        id = row[0]
        lng = row[1]
        lat = row[2]
        row_result = {"id": id, "lng": lng, "lat": lat}
        id_results.append(row_result)
    socketio.emit("postIdResults", {"idResults": id_results}, broadcast=True)

# -----------------------------------------------DELETE---------------------------------------------------------#

# ----------------------------------------------------#
# Websocket Deletes the interface of a single point
# ----------------------------------------------------#
@socketio.on("deletePoint")
def delete_point(get_data):
    try:
        table = "bmapsvf_qinhuai"
        print('-----The system starts to delete the sampling point-----')
        with mysql() as cursor:
            cursor.execute(
                "Delete from {} where panoid = %s".format(table), (get_data))
            print('-----Deleting a single sampling point succeeded-----')
            socketio.emit("getDeletePoint", {"msg": "Successfully delete!"}, broadcast=True)

            cursor.execute("SELECT panoid, lng, lat, fisheye, fisheye_seg, svf FROM {}".format(table))
            result = cursor.fetchall()
            panorama_results = []
            for row in result:
                panoid = row[0]
                lng = row[1]
                lat = row[2]
                fisheye_pro = base64.b64encode(row[3])
                fisheye = fisheye_pro.decode("utf-8")
                fisheye_seg_pro = base64.b64encode(row[4])
                fisheye_seg = fisheye_seg_pro.decode("utf-8")
                svf = row[5]
                row_result = {"panoid": panoid, "lng": lng, "lat": lat, "fisheye": fisheye, "fisheye_seg": fisheye_seg,
                              "svf": svf}
                panorama_results.append(row_result)
            socketio.emit("getSecondPoints", {"secondPoints": panorama_results}, broadcast=True)
    except Exception as e:
        print(e)
        socketio.emit("getError", str(e))

# --------------------------------------------------------#
# Websocket Deletes the interface of the csv load point
# --------------------------------------------------------#
@socketio.on("deleteCsvPoints")
def delete_csv_point(get_data):
    try:
        table = "bmapsvf_csv"
        print('-----The system starts to delete the sampling point-----')
        with mysql() as cursor:
            cursor.execute(
                "Delete from {} where panoid = %s".format(table), (get_data))
            print('-----Deleting a single sampling point succeeded-----')
            socketio.emit("getDeleteCsvPoint", {"msg": "Successfully delete!"}, broadcast=True)

            cursor.execute("SELECT panoid, lng, lat, fisheye, fisheye_seg, svf FROM {}".format(table))
            result = cursor.fetchall()
            panorama_results = []
            for row in result:
                panoid = row[0]
                lng = row[1]
                lat = row[2]
                fisheye_pro = base64.b64encode(row[3])
                fisheye = fisheye_pro.decode("utf-8")
                fisheye_seg_pro = base64.b64encode(row[4])
                fisheye_seg = fisheye_seg_pro.decode("utf-8")
                svf = row[5]
                row_result = {"panoid": panoid, "lng": lng, "lat": lat, "fisheye": fisheye, "fisheye_seg": fisheye_seg,
                              "svf": svf}
                panorama_results.append(row_result)
            socketio.emit("getSecondCsvPoints", {"secondCsvPoints": panorama_results}, broadcast=True)
    except Exception as e:
        print(e)
        socketio.emit("getCsvError", str(e))

if __name__ == "__main__":
     # socketio.run(app, host='127.0.0.1', port=5000, debug=True, threaded=True, logger=True, engineio_logger=True)
     socketio.run(app, debug=True, threaded=True, logger=True, engineio_logger=True)
