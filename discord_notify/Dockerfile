FROM amazonlinux:latest

RUN yum update -y
RUN yum install -y python3-pip zip

RUN mkdir -p /app
ADD requirements.txt /app
ADD handler.py /app
ADD rrule_parser/rrule_parser.py /app/rrule_parser
ADD rrule_parser/requirements.txt /app/rrule_parser

WORKDIR /app
RUN pip3 install -t . -r requirements.txt
RUN pip3 install -t . -r rrule_parser/reqirements.txt
RUN zip -r zip.zip .