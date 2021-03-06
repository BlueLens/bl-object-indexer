FROM bluelens/ubuntu-16.04:py3

RUN mkdir -p /opt/app/model

RUN apt-get update
RUN apt-get install -y curl
RUN curl https://s3.ap-northeast-2.amazonaws.com/bluelens-style-model/prod/classification/inception_v3/classify_image_graph_def.pb -o /opt/app/model/classify_image_graph_def.pb

ENV CLASSIFY_GRAPH /opt/app/model/classify_image_graph_def.pb

RUN mkdir -p /usr/src/app

WORKDIR /usr/src/app

COPY . /usr/src/app
RUN pip3 install --no-cache-dir -r requirements.txt

#RUN curl https://s3.ap-northeast-2.amazonaws.com/bluelens-style-model/classification/inception_v3/classify_image_graph_def.pb -o /usr/src/app/model/classify_image_graph_def.pb

#ENV PYTHONPATH $PYTHONPATH:/usr/src/app/faiss
#ENV CLASSIFY_GRAPH ./model/classify_image_graph_def.pb

CMD ["python3", "main.py"]
