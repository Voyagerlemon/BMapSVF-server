# camera-ready

import pickle
import sys

import cv2
import matplotlib
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.data
from torch.autograd import Variable

from datasets import \
    DatasetVal  # (this needs to be imported before torch,
# because cv2 needs to be imported before torch for some reason)
from model.deeplabv3 import DeepLabV3

matplotlib.use("Agg")

sys.path.append("/root/deeplabv3")
sys.path.append("/root/deeplabv3/model")
sys.path.append("/root/deeplabv3/utils")

if __name__ == '__main__':
    trainId_to_id = {
        0: 7,
        1: 8,
        2: 11,
        3: 12,
        4: 13,
        5: 17,
        6: 19,
        7: 20,
        8: 21,
        9: 22,
        10: 23,
        11: 24,
        12: 25,
        13: 26,
        14: 27,
        15: 28,
        16: 31,
        17: 32,
        18: 33,
        19: 0
    }
    trainId_to_id_map_func = np.vectorize(trainId_to_id.get)

    batch_size = 2

    network = DeepLabV3("eval_val_for_metrics", project_dir="/root/deeplabv3").cuda()
    network.load_state_dict(torch.load("E:/Master/ResearchDataProcessing/DeepLearning/deeplabv3/training_logs/model_1"
                                       "/checkpoints/model_1_epoch_1000.pth"))

    val_dataset = DatasetVal(cityscapes_data_path="E:/DataSet/cityscapes",
                             cityscapes_meta_path="E:/DataSet/cityscapes")

    num_val_batches = int(len(val_dataset) / batch_size)

    print("num_val_batches:", num_val_batches)

    val_loader = torch.utils.data.DataLoader(dataset=val_dataset,
                                             batch_size=batch_size, shuffle=False,
                                             num_workers=1)

    with open("E:/DataSet/cityscapes/class_weights.pkl", "rb") as file:  # (needed for python3)
        class_weights = np.array(pickle.load(file))
    class_weights = torch.from_numpy(class_weights)
    class_weights = Variable(class_weights.type(torch.FloatTensor)).cuda()

    # loss function
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)

    network.eval()  # (set in evaluation mode, this affects BatchNorm and dropout)
    batch_losses = []
    for step, (imgs, label_imgs, img_ids) in enumerate(val_loader):
        with torch.no_grad():  # (corresponds to setting volatile=True in all variables,
            # this is done during inference to reduce memory consumption)
            imgs = Variable(imgs).cuda()  # (shape: (batch_size, 3, img_h, img_w))
            label_imgs = Variable(label_imgs.type(torch.LongTensor)).cuda()  # (shape: (batch_size, img_h, img_w))

            outputs = network(imgs)  # (shape: (batch_size, num_classes, img_h, img_w))

            # compute the loss:
            loss = loss_fn(outputs, label_imgs)
            loss_value = loss.data.cpu().numpy()
            batch_losses.append(loss_value)

            ########################################################################
            # save data for visualization:
            ########################################################################
            outputs = F.interpolate(outputs, size=(1024, 2048),
                                    mode="bilinear")  # (shape: (batch_size, num_classes, 1024, 2048))

            outputs = outputs.data.cpu().numpy()  # (shape: (batch_size, num_classes, 1024, 2048))
            pred_label_imgs = np.argmax(outputs, axis=1)  # (shape: (batch_size, 1024, 2048))
            pred_label_imgs = pred_label_imgs.astype(np.uint8)

            for i in range(pred_label_imgs.shape[0]):
                pred_label_img = pred_label_imgs[i]  # (shape: (1024, 2048))
                img_id = img_ids[i]

                # convert pred_label_img from trainId to id pixel values:
                pred_label_img = trainId_to_id_map_func(pred_label_img)  # (shape: (1024, 2048))
                pred_label_img = pred_label_img.astype(np.uint8)

                cv2.imwrite(network.model_dir + "/" + img_id + "_pred_label_img.png", pred_label_img)

    val_loss = np.mean(batch_losses)
    print("val loss: %g" % val_loss)
