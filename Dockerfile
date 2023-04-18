# This dockerfile unses the python:3.7.13 image
# VERSION 1 - EDITION 1
# Author: imqtan

# Base image to use, this must be set as the first line
FROM python:3.7.13

# Maintainer:docker_user<docker_user@email.com>
MAINTAINER xuhy 1727317079@qq.com

COPY . /Flask_panorama

WORKDIR /Flask_panorama

RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["python"]

CMD ["app.py"]
