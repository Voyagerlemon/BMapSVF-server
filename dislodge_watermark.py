# -*- coding: utf-8 -*-
"""
@Author: xuhy
@Date: 2022/8/28 17:22
@LastEditTime: 2022/8/28 17:22
@LastEditors: xuhy
@FilePath: dislodge_watermark.py
@Description: 去除街景的百度水印
"""
import cv2
import numpy as np

# -----------------------------------------#
# 提取水印
# -----------------------------------------#
img_panorama = cv2.imread('img_panorama/panorama_00/once.png')
img_roi = img_panorama[458:503, 9:145]
img_roi_hsv = cv2.cvtColor(img_roi, cv2.COLOR_BGR2HSV)

# -----------------------------------------#
# 处理蓝色百度图标, 创建蓝色水印蒙层
# -----------------------------------------#
lower_blue = np.array([100, 43, 46])
upper_blue = np.array([124, 255, 255])
mask_blue = cv2.inRange(img_roi_hsv, lower_blue, upper_blue)

# -----------------------------------------#
# 对蓝色水印进行膨胀操作
# -----------------------------------------#
kernel_size = np.ones((3, 3), np.uint8)
dilate_blue = cv2.dilate(mask_blue, kernel_size, iterations=1)

# -----------------------------------------#
# 修补蓝色水印
# -----------------------------------------#
fix_blue = cv2.inpaint(img_roi, dilate_blue, 5, flags=cv2.INPAINT_TELEA)
seg_path1 = "img_panorama/panorama_00/once2.png"
cv2.imwrite(seg_path1, fix_blue)
# -----------------------------------------#
# 处理红色水印
# -----------------------------------------#
lower_red = np.array([0, 43, 46])
upper_red = np.array([10, 255, 255])
img_roi1_hsv = cv2.cvtColor(fix_blue, cv2.COLOR_BGR2HSV)
mask_red = cv2.inRange(img_roi1_hsv, lower_red, upper_red)
dilate_red = cv2.dilate(mask_red, kernel_size, iterations=1)

# -----------------------------------------#
# 修补红色水印
# -----------------------------------------#
fix_red = cv2.inpaint(fix_blue, dilate_red, 5, flags=cv2.INPAINT_TELEA)
seg_path = "img_panorama/panorama_00/once1.png"
cv2.imwrite(seg_path, fix_red)
