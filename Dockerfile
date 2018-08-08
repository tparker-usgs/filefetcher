# pull daily files
#
# BUILD-USING:  docker build -t webrelaytwiddler .
# RUN-USING:    docker run --detach=true --name webrelaytwiddler webrelaytwiddler
#

# can't use onbuild due to SSL visibility
FROM python:3.7

RUN apt-get update && apt-get -y install cron

WORKDIR /root/.pip
ADD support/pip.conf .

WORKDIR /app/webrelaytwiddler
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt # 1

ADD VERSION .
ADD webrelaytwiddler.py .
RUN chmod 755 webrelaytwiddler.py
ADD support/cron-webrelaytwiddler .
ADD support/run_crond.sh  .
RUN chmod 755 run_crond.sh

CMD ["/app/webrelaytwiddler/run_crond.sh"]
