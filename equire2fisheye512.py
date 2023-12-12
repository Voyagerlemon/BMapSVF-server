# -*- coding: utf-8 -*-
"""
@Project: Flask_panorama
@Author: xuhy xuhaiyangw@163.com
@Date: 2023/3/12 16:10
@LastEditors: xuhy xuhaiyangw@163.com
@FilePath: equire2fisheye512.py
@Description: 1024*512--->512*512
"""
from PIL import Image
import numpy as np


def equire2fisheye(panorama, isSegFisheye):
    img = Image.open(panorama)
    width, height = img.size
    img = img.crop((0, 0, width, height / 2))
    width, height = img.size
    red, green, blue = img.split()
    red = np.asarray(red)
    green = np.asarray(green)
    blue = np.asarray(blue)
    fisheye = np.ndarray(shape=(512, 512, 3), dtype=np.uint8)
    fisheye.fill(0)

    x = np.arange(0, 512, dtype=float)
    x = x / 511.0
    x = (x - 0.5) * 2
    x = np.tile(x, (512, 1))
    y = x.transpose()
    dist2ori = np.sqrt((y * y) + (x * x))
    angle = dist2ori * 90.0
    angle[np.where(angle <= 0.000000001)] = 0.000000001
    radian = angle * 3.1415926 / 180.0
    fisheye_weight = np.sin(radian) / (angle / 90.0)

    x2 = np.ndarray(shape=(512, 512), dtype=float)
    x2.fill(0.0)
    y2 = np.ndarray(shape=(512, 512), dtype=float)
    y2.fill(1.0)
    cosa = (x * x2 + y * y2) / np.sqrt((x * x + y * y) * (x2 * x2 + y2 * y2))
    lon = np.arccos(cosa) * 180.0 / 3.1415926
    indices = np.where(x > 0)
    lon[indices] = 360.0 - lon[indices]
    lon = 360.0 - lon
    lon = 1.0 - (lon / 360.0)
    outside = np.where(dist2ori > 1)
    lat = dist2ori
    srcx = (lon * (width - 1)).astype(int)
    srcy = (lat * (height - 1)).astype(int)
    srcy[np.where(srcy > 255)] = 0
    indices = (srcx + srcy * width).tolist()

    red = np.take(red, np.array(indices))
    green = np.take(green, np.array(indices))
    blue = np.take(blue, np.array(indices))
    red[outside] = 0
    green[outside] = 0
    blue[outside] = 0

    svf = -1
    sky_mask = 65536 * 180 + 256 * 130 + 70
    if isSegFisheye == 1:
        all_pixels = 65536 * red + 256 * green + blue
        sky_indices = np.where(all_pixels == sky_mask)

        background_indices = np.where(all_pixels != 0)
        svf = np.sum(fisheye_weight[sky_indices]) / np.sum(fisheye_weight[background_indices])

        red[sky_indices] = 180
        green[sky_indices] = 130
        blue[sky_indices] = 70

    red[outside] = 255
    green[outside] = 255
    blue[outside] = 255
    fisheye = np.dstack((red, green, blue))
    return Image.fromarray(fisheye), svf
