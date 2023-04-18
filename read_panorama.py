# -*- coding: utf-8 -*-
"""
@Author: xuhy
@Date: 2022/8/3 16:14
@LastEditTime: 2022/8/3 16:14
@LastEditors: xuhy
@FilePath: read_panorama.py
@Description: 实时验证并分割全景静态图
"""
import cv2
import time
import base64
import numpy as np
import torch.utils.data
from datasets import DatasetSeq
from torch.autograd import Variable
from model.deeplabv3 import DeepLabV3
from utils.utils import label_img_to_color
from equire2fisheye512 import equire2fisheye

#######################################################################################
# 转换base64格式
#######################################################################################
def seg_result_img(seg_path):
    with open(seg_path, "rb") as f:
        img_stream = f.read()
        img_stream = base64.b64encode(img_stream).decode()
    return img_stream


def seg_result_cv(seg_path):
    img_stream = cv2.imencode('.png', seg_path)[1]
    img_stream = str(base64.b64encode(img_stream))[2:-1]
    return img_stream


# -----------------------------------------#
# 验证并分割全景静态图
# read_panorama接口
# -----------------------------------------#
def real_time_segmentation(root_directory):
    time_start = time.time()
    batch_size = 2
    network = DeepLabV3("eval_seq", project_dir=root_directory).cuda()
    network.load_state_dict(torch.load("training_logs/model_1/checkpoints/model_1_epoch_1000.pth"))

    for sequence in ["00"]:
        val_dataset = DatasetSeq(cityscapes_data_path=root_directory, cityscapes_meta_path=root_directory,
                                 sequence=sequence)
        val_loader = torch.utils.data.DataLoader(dataset=val_dataset, batch_size=batch_size, shuffle=False,
                                                 num_workers=1)
        network.eval()
        unsorted_img_ids = []
        for step, (img_all, img_ids) in enumerate(val_loader):
            with torch.no_grad():
                img_all = Variable(img_all).cuda()
                outputs = network(img_all)
                outputs = outputs.data.cpu().numpy()
                pred_label_imgs = np.argmax(outputs, axis=1)
                pred_label_imgs = pred_label_imgs.astype(np.uint8)

                for i in range(pred_label_imgs.shape[0]):
                    pred_label_img = pred_label_imgs[i]
                    img_id = img_ids[i]
                    pred_label_img_color = label_img_to_color(pred_label_img)
                    seg_path = root_directory + "/img_recognized/" + img_id + "_seg.png"
                    seg_fisheye_path = root_directory + "/img_fisheye/" + img_id + "_fisheye.png"
                    cv2.imwrite(seg_path, pred_label_img_color)
                    fisheye_result = cv2.imread(seg_path)
                    cv2.imwrite(seg_fisheye_path, fisheye_result)
                    # equire2fisheye(seg_fisheye_path, 0)  # 转换为鱼眼
                    unsorted_img_ids.append(img_id)

    time_end = time.time()
    total_cost = time_end - time_start
    return total_cost, seg_path, seg_fisheye_path
