FROM python:3

# install dependancies
COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt

# make app directory and add source
RUN mkdir /opt/midea2mqtt
ADD *.py /opt/midea2mqtt/

# make conf directory (map this to your local filesystem in docker-compose.yml)
RUN mkdir /etc/opt/midea2mqtt
ADD *.yml /etc/opt/midea2mqtt/

# set entrypoint
CMD ["python", "/opt/midea2mqtt/midea2mqtt.py"]
