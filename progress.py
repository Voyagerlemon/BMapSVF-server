# -*- coding: utf-8 -*-
"""
@Author: xuhy
@Date: 2022/8/15 17:15
@LastEditTime: 2022/8/15 17:15
@LastEditors: xuhy
@FilePath: progress.py
@Description: 进度条
"""
import time
from multiprocessing import Pool
from flask_cors import CORS
from tqdm import tqdm
from flask import Flask, make_response, jsonify

app = Flask(__name__)
CORS(app)


def do_work(x):
    time.sleep(x)
    return x


total = 5  # 总任务数
tasks = range(total)
pbar = tqdm(total=len(tasks))


@app.route('/run/')
def run():
    """执行任务"""
    results = []
    with Pool(processes=2) as pool:
        for _result in pool.imap_unordered(do_work, tasks):
            results.append(_result)
            if pbar.n >= total:
                pbar.n = 0  # 重置
            pbar.update(1)
    response = make_response(jsonify(dict(results=results)))
    return response


@app.route('/progress/')
def progress():
    """查看进度"""
    response = make_response(jsonify(dict(n=pbar.n, total=pbar.total)))
    return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9001, debug=True)
