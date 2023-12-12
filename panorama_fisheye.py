# -*- coding: utf-8 -*-
"""
@Author: xuhy xuhaiyangw@163.com
@Date: 2022/8/1 20:29
@LastEditTime: 2022/8/1 20:29
@LastEditors: xuhy xuhaiyangw@163.com
@FilePath: panorama_fisheye.py
@Description: Convert the panorama to a fisheye image
"""
import cv2
import math
import numpy as np


def panorama_fisheye(img_name):
    img = cv2.imread(img_name)
    rows, cols, rgb = img.shape
    cx = cols / (2 * math.pi)
    cy = cols / (2 * math.pi)
    r0 = int(cols / (2 * math.pi))  # The radius of the fisheye image
    img_fisheye = np.zeros([250, 250, 4], np.uint8)
    for xf in range(250):
        for yf in range(250):
            r = math.sqrt((xf - cx) ** 2 + (yf - cy) ** 2)
            if yf < cx:
                theta = 3 * math.pi / 2 - math.atan((xf - cy) / (yf - cx))
            else:
                theta = math.pi / 2 - math.atan((xf - cy) / (yf - cx))
            yc = int(theta * 1024 / (2 * math.pi))
            xc = int(r * 512 / r0)
            if xc <= 256 and yc < 1024:
                img_fisheye[xf, yf] = np.append(img[xc, yc], -1)

        clip_fisheye = img_fisheye[77:250, 77:250]
        horiz_img = cv2.flip(clip_fisheye, 1, dst=None)
        cv2.imwrite(img_name, horiz_img, [int(cv2.IMWRITE_PNG_COMPRESSION), 0])
