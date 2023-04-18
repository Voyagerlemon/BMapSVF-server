# -*- coding: utf-8 -*-
"""
@Author: xuhy
@Date: 2022/8/11 18:03
@LastEditTime: 2022/8/11 18:03
@LastEditors: xuhy
@FilePath: calculate_fisheye.py
@Description: 通过计算鱼眼图像的天空颜色的像素，得出天空可视域
"""
import os
import prettytable
from PIL import Image
from collections import Counter


# -----------------------------------------#
# 计算一张图像
# -----------------------------------------#
def calculate_single_fisheye():
    file_path = 'img_fisheye'
    f = open(file_path[:-7] + 'result.txt', 'w')
    sky_view_factor = 0.00
    for root, dirs, files, in os.walk(file_path):
        img_fisheye = files[1]
        img_use_fisheye = Image.open(file_path + "/" + img_fisheye)
        w, h = img_use_fisheye.size
        img_data = img_use_fisheye.load()

        colors = []
        for x in range(w):
            for y in range(h):
                color = img_data[x, y]
                hex_color = '#' + ''.join([hex(c)[2:].rjust(2, '0') for c in color])
                colors.append(hex_color)

        color_table = prettytable.PrettyTable(['Color', 'Count', 'Percentage'])
        for color, count in Counter(colors).items():
            # total_pixel = sum(Counter(colors).values())
            color_table.add_row([color, count, (count / 21001)])

        for k, v in Counter(colors).items():
            if k == "#b48246ff":
                sky_view_factor = v / 21001
                f.write(img_fisheye[:-4] + ' ' + str(sky_view_factor) + '\n')
    f.close()
    return sky_view_factor


def calculate_total_fisheye(exist_path):
    fisheye_path = exist_path
    f = open(fisheye_path[:-7] + 'result.txt', 'w')
    sky_view_factor = 0.00

    for root, dirs, files, in os.walk(fisheye_path):
        for img_total_fisheye in files:
            total_fisheye = Image.open(fisheye_path + "/" + img_total_fisheye)
            w, h = total_fisheye.size
            img_data = total_fisheye.load()
            colors = []
            for x in range(w):
                for y in range(h):
                    color = img_data[x, y]
                    hex_color = '#' + ''.join([hex(c)[2:].rjust(2, '0') for c in color])
                    colors.append(hex_color)
            color_table = prettytable.PrettyTable(['Color', 'Count', 'Percentage'])
            for color, count in Counter(colors).items():
                # total_pixel = sum(Counter(colors).values())
                color_table.add_row([color, count, (count / 21001)])
            for k, v in Counter(colors).items():
                if k == "#b48246ff":
                    sky_view_factor = v / 21001
                    f.write(total_fisheye[:-4] + '   ' + str(sky_view_factor) + '\n')
    f.close()
    return sky_view_factor
