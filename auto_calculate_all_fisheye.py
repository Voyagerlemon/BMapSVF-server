# -*- coding: utf-8 -*-
"""
@Project: BMapSVF_Server
@Author: xuhy xuhaiyangw@163.com
@Date: 2023/3/9 21:43
@LastEditors: xuhy xuhaiyangw@163.com
@FilePath: auto_calculate_all_fisheye.py
@Description: 
"""
import cv2
import os
import math
import sys

# Divide the picture into circles
if len(sys.argv) == 2:
    filepath = sys.argv[1]
    files = os.listdir(filepath)
    x0 = 86  # Center x coordinates
    y0 = 86  # Center y coordinates
    f = open(filepath[:-7] + 'result.txt', 'w')

    # Start processing pictures
    for inputimg in files:
        r = 82
        fisheye_img = cv2.imread(filepath + '\\' + inputimg)
        svf = 0.00  # Sky proportion, default
        for index in range(1, 28):
            circled_img = cv2.imread(filepath + '\\' + inputimg)
            cv2.circle(circled_img, (86, 86), r, [0, 255, 255])
            cv2.circle(circled_img, (86, 86), r - 1, [0, 255, 255])
            cv2.circle(circled_img, (86, 86), r - 2, [0, 255, 255])
            circle_points = []
            sky_points = []
            tree_points = []
            for i in range(0, 173):
                for j in range(0, 173):
                    if circled_img[i][j][0] == 0 and circled_img[i][j][1] == 255 and circled_img[i][j][2] == 255:
                        circle_points.append([i, j])
            # Calculate the sky proportion
            for point in circle_points:
                x = point[0]
                y = point[1]
                if fisheye_img[x][y][0] in range(190, 256) and fisheye_img[x][y][1] in range(190, 256) and \
                        fisheye_img[x][y][2] in range(190, 256):
                    # fisheye_img[x][y] =[0,255,255]
                    sky_points.append(point)

            print('Total pixel', len(circle_points), '个')
            sky = len(sky_points) / len(circle_points)
            print('Sky pixel', len(sky_points), 'proportion:', sky)
            svf = svf + math.sin(math.pi * (2 * index - 1) / 54) * sky

            r = r - 3
        svf = (math.pi / 54) * svf
        print(inputimg + 'Complete the calculation')
        print(svf)

    f.close()


