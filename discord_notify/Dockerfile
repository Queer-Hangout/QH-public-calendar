FROM amazonlinux:latest

RUN yum update -y
RUN yum install -y python3-pip zip

RUN mkdir -p /app
ADD requirements.txt /app
ADD handler.py /app

WORKDIR /app
RUN pip3 install -t . -r requirements.txt
RUN zip -r zip.zip .