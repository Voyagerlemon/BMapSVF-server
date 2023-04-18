"""
Author: xuhy
Date: 2022-07-22 11:20:02
LastEditors: xuhy
LastEditTime: 2022-07-25 17:34:31
FilePath: app.py
Description: BMapSVF API
"""
import os
import cv2
import requests
import json
import csv
import time
import base64
import pymysql
import contextlib
import datetime
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
# 配置会话密钥
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=12)
app.config['JSON_AS_ASCII'] = False
# app.config['SESSION_TYPE'] = "redis"  # session类型为redis
# app.config['SESSION_PERMANENT'] = True  # 如果设置为True，则关闭浏览器session就失效

socketio = SocketIO()
socketio.init_app(app, cors_allowed_origins='*')
CORS(app)

cur_path = os.path.abspath(os.path.dirname(__file__))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')



@app.route('/')
def index():
    return '<h2>Welcome to the BMapSVF server!</h2>'

@socketio.on('message')
def handle_message(message):
    message = urllib.parse.unquote(message)
    print(message)
    send(message, broadcast=True)


# -----------------------------------------#
# 连接、断开连接与服务器发生异常处理
# -----------------------------------------#
@socketio.on('connect', namespace='/save')
def save_connect():
    print("Client connected")


@socketio.on('disconnect', namespace='/save')
def save_disconnect():
    print('Client disconnected')

@socketio.on_error('/save')
def error_handler_chat(e):
    print('An error has occurred: ' + str(e))

# -----------------------------------------#
# 使用Websocket登录接口
# -----------------------------------------#
@socketio.on("login")
def login(get_data):
    username = get_data.get("username")
    password = get_data.get("password")
    if username == "admin" and password == "gis5566":
        token = generate_token(username)
        if certify_token(username, token):
            socketio.emit("loginSuccess", {"status": 200, "token":token, "msg": "登录成功了"}, broadcast=True)
        else:
            return
    else:
        socketio.emit("loginError", {"status": 400, "msg": "账号或密码错误"}, broadcast=True)
    return token

# -----------------------------------------#
# 定义上下文管理器，自动开启连接与关闭
# -----------------------------------------#
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

# -----------------------------------------#
# Websocket处理百度全景图接口
# -----------------------------------------#
@socketio.on("postSavePanorama")
def save_panorama(get_data):
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

    # 将二进制数据转换为图像对象
    img_panorama = Image.open(BytesIO(panorama))
    img_panorama.save(cur_path + "/img_panorama/panorama_00/once.png", "PNG")
    img_fisheye = equire2fisheye(cur_path + "/img_panorama/panorama_00/once.png", 0)

    output_panorama = BytesIO()
    img_fisheye[0].save(output_panorama, format='PNG')
    fisheye = output_panorama.getvalue()

    print('-----开始进行语义分割-----')
    socketio.emit("getReadSegInfo", {"msg": "Semantic segmentation is underway!"}, broadcast=True)
    seg_result = real_time_segmentation(cur_path)
    total_cost = seg_result[0]
    print("total time:", f"{total_cost}" + "s")
    socketio.emit("getReadPanorama", {"msg": f"Semantic segmentation is complete, and takes {total_cost:.2f} s. Calculating SVF!",
                                   "total_cost": total_cost}, broadcast=True)

    img = cv2.imread(seg_result[1], 1)
    retval, buffer = cv2.imencode('.png', img)
    panorama_seg = np.array(buffer).tobytes()

    print('-----开始计算svf-----')
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
        print('-----百度全景图及相关信息成功存入至数据库-----')
    socketio.emit("getSuccessPanorama", {"msg": "Data storage successfully!"}, broadcast=True)

# -----------------------------------------#
# Websocket获取百度全景处理结果接口
# -----------------------------------------#
@socketio.on("postPanoramaResults")
def read_panorama(get_data):
    resquest_info = get_data.encode('utf-8').decode('utf-8')
    print(resquest_info)
    with mysql() as cursor:
        cursor.execute("SELECT panoid, lng, lat, fisheye, fisheye_seg, svf FROM bmapsvf_test")
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
    socketio.emit("getPanoramaResults", {"panoramaResults": panorama_results}, broadcast=True)

# -----------------------------------------#
# Http发送csv文件
# -----------------------------------------#
@app.route('/upload', methods=['POST'], strict_slashes=False)
def upload():
    table = "bmapsvf_transform"
    time_stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    file_csv = request.files['file']
    file_csv.save(cur_path+ f"/csv/file_{time_stamp}.csv")
    print('-----csv文件上传成功-----')
    csv_results = []
    # 服务地址
    host = "https://api.map.baidu.com"
    uri = "/geoconv/v1/"
    ak = "YniOI8mkAeMNRPNR4DkFu5LQP9ArmWGn"
    with open(cur_path+ f"/csv/file_{time_stamp}.csv", encoding='utf-8',newline='') as csvfile:
      reader = csv.DictReader(csvfile)
      for row in reader:
          wgs84_lng = float(row["lng"])
          wgs84_lat = float(row["lat"])
          params_location = {
              "coords": row["lng"]+','+row["lat"],
              "from": "1",
              "to": "5",
              "ak": ak,
          }
          response = requests.get(url=host+uri, params= params_location)
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
                  row_result = {"lng": bd09_lng, "lat":  bd09_lat}
                  csv_results.append(row_result)
    return jsonify({"status": 200, "msg": "Csv file uploaded successfully!", "csvResults": csv_results})

# -----------------------------------------#
# Websocket处理通过csv获取的百度全景接口
# -----------------------------------------#
@socketio.on("postCsvPanoramas")
def csv_panorama(get_data):
    table = "bmapsvf_csv"
    for item in get_data:
        srcPath = item["srcPath"]
        panoid = item["panoid"]
        date = item["date"]
        lng = item["lng"]
        lat = item["lat"]
        descr = item["description"].encode('utf-8').decode('utf-8')
        result = urllib.request.urlopen(srcPath)
        panorama = result.read()
        # 将二进制数据转换为图像对象
        img_panorama = Image.open(BytesIO(panorama))
        img_panorama.save(cur_path + "/img_panorama/panorama_00/once.png", "PNG")
        img_fisheye = equire2fisheye(cur_path + "/img_panorama/panorama_00/once.png", 0)

        output_panorama = BytesIO()
        img_fisheye[0].save(output_panorama, format='PNG')
        fisheye = output_panorama.getvalue()

        print('-----开始进行语义分割-----')
        socketio.emit("getReadSegInfo", {"msg": f"{panoid} point is currently undergoing semantic segmentation!"}, broadcast=True)
        seg_result = real_time_segmentation(cur_path)
        total_cost = seg_result[0]
        print("total time:", f"{total_cost}" + "s")
        socketio.emit("getReadPanorama",
                      {"msg": f"Semantic segmentation of {panoid} point has been complete and it took {total_cost:.2f}s. Calculating the SVF!",
                       "total_cost": total_cost}, broadcast=True)

        img = cv2.imread(seg_result[1], 1)
        retval, buffer = cv2.imencode('.png', img)
        panorama_seg = np.array(buffer).tobytes()

        print('-----开始计算svf-----')
        img_seg_fisheye = equire2fisheye(seg_result[2], 1)
        output_seg_fisheye = BytesIO()
        img_seg_fisheye[0].save(output_seg_fisheye, format='PNG')
        fisheye_seg = output_seg_fisheye.getvalue()
        svf = img_seg_fisheye[1]

        socketio.emit("getCalculateSVF", {"msg": f"The SVF calculation of {panoid} point has been completed!", "svf": svf}, broadcast=True)

        with mysql() as cursor:
            cursor.execute(
                "INSERT INTO {}(panoid, date, lng, lat, description, panorama, fisheye, panorama_seg, fisheye_seg, svf) "
                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(
                    table),
                (panoid, date, lng, lat, descr, panorama, fisheye, panorama_seg, fisheye_seg, svf))
            print('-----百度全景图及相关信息成功存入至数据库-----')
    socketio.emit("getSuccessPanorama", {"msg": "All data has been stored successfully!"}, broadcast=True)

# -----------------------------------------#
# Websocket获取百度全景处理结果接口
# -----------------------------------------#
@socketio.on("postCsvPanoramaResults")
def read_csv_panorama(get_data):
    resquest_info = get_data.encode('utf-8').decode('utf-8')
    print(resquest_info)
    with mysql() as cursor:
        cursor.execute("SELECT panoid, lng, lat, fisheye, fisheye_seg, svf FROM bmapsvf_csv")
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
    socketio.emit("getCsvPanoramaResults", {"panoramaResults": panorama_results}, broadcast=True)

# -----------------------------------------#
# Websocket的WGS84-->BD09坐标
# -----------------------------------------#
@socketio.on("transformWGSCoordinate")
def transform_wgs_coordinate(get_data):
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
    socketio.emit("getBD09Coordinate", {"row_result":  row_result}, broadcast=True)

if __name__ == "__main__":
     # socketio.run(app, host='127.0.0.1', port=5000, debug=True, threaded=True, logger=True, engineio_logger=True)
     socketio.run(app, debug=True, threaded=True, logger=True, engineio_logger=True)
