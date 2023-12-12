# BMapSVF-Server

# Feature

- The image semantic segmentation algorithm **DeeplabV3** is constructed.
- The best **projection algorithm** for converting panoramic image into fisheye image is written.
- Write the most **RESTful** Web API.
- The TCP based full-duplex communication protocol **WebSocket** is used.
- Python's **Flask** framework is used.
- Using **MySQL** database, the design of the data table can refer to the example [folder](./temp).

# Directory organization specification

```shell
├── csv --------------------------- Store the location information of the sampling   ----------------------------------- point
├── evaluation --------------------------- Inference function for Deeplabv3
├── img_fisheye ---------------------------- Fisheye image
├── img_panorama ---------------------------- Panorama
├── img_recognized ---------------------------- Image after semantic segmentation
├── model
│ ├── aspp.py
│ ├── deeplabv3.py
│ ├── resnet.py
├── pretrained_models
│ ├── resnet
├── static
│ ├── favicon.ico ---------------------------- Icon file
├── temp ---------------------------- Sample data
├── training_logs
├── utils
├── .gitignore
├── app.py
├── auto_calculate_all_fisheye.py ---------------------------- Another algorithm to   ------------------------ calculate SVF from fisheye images can be used for reference
├── datasets.py ---------------------------- Load the training dataset
├── Dockerfile
├── equire2fisheye512.py ---------------------------- To fisheye image
├── generate_token.py
├── read_panorama.py ---------------------------- Verify and segment panoramic static ------------------------------------------------- images in real time
├── README.md
├── requirements.txt
├── train.py
```

# Install

### 1、Create environment

```shell
conda create -n bmapsvf_server python==3.7/3.8/3.9/3.10
(All of these python versions are available; the others are not tested)
conda activate bmapsvf_server
```

### 2、 Install package

```shell
git clone https://github.com/Voyagerlemon/BMapSVF-server.git
cd BMapSVF-server
pip install -r requirements.txt
```

### 3、 Run

```shell
python app.py
or
flask run
```

> **<span style="color: red">Note:</span>** **Before you can start running the project, you need to create a MySQL database, named panorama, or you can modify the code depending on your situation**

```python
# app.py 116-126
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
```

# Citation

```text
@misc{BMapSVF-Server,
  title={BMapSVF-Server},
  url={https://github.com/Voyagerlemon/BMapSVF-server},
  note={Open source software available from https://github.com/Voyagerlemon/BMapSVF-server},
  author={Voyagerlemon},
  year={2023},
}
```