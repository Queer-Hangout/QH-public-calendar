FROM amazon/aws-lambda-python:3.9

RUN yum update -y && \
    yum install -y python3 python3-dev python3-pip gcc && \
    rm -Rf /var/cache/yum

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY model ./model
RUN pip install -r model/requirements.txt

COPY __init__.py ./
COPY handler.py ./

CMD ["handler.handler"]