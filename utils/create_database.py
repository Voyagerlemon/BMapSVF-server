# -*- coding: utf-8 -*-
"""
@Project: BMapSVF-Server
@Author: xuhy xuhaiyangw@163.com
@Date: 2024/3/26 15:17
@LastEditors: xuhy xuhaiyangw@163.com
@FilePath: create_database.py.py
@Description: Create database
"""
import pymysql.cursors


# Function to connect to the MySQL database and execute a command
def create_database_and_table():
    # Connection details should be customized as per your MySQL server
    connection = pymysql.connect(host='127.0.0.1',
                                 user='root',
                                 password='gis5566&',
                                 port=3306,
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS panorama;")
            connection.commit()
            cursor.execute("USE bmapsvf_qinhuai;")

            create_table_command = """
            CREATE TABLE IF NOT EXISTS `collection_bsv` (
                `id` int NOT NULL AUTO_INCREMENT,
                `panoid` varchar(255) DEFAULT NULL,
                `date` date DEFAULT NULL,
                `lng` double DEFAULT NULL,
                `lat` double DEFAULT NULL,
                `description` varchar(255) DEFAULT NULL,
                `panorama` longblob,
                `panorama_seg` longblob,
                `fisheye` longblob,
                `fisheye_seg` longblob,
                `svf` float DEFAULT NULL,
                PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            cursor.execute(create_table_command)
            connection.commit()
        print("The creation is successful.")
    finally:
        connection.close()


if __name__ == "__main__":
    create_database_and_table()
