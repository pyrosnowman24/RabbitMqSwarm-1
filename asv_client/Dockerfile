FROM python:3

RUN pip install numpy
RUN pip install pika
RUN pip install pyyaml

ADD asv_client.py /
ADD config.yaml /
CMD [ "python", "asv_client.py" ]
