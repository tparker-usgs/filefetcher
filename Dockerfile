# pull daily files
#
# BUILD-USING:  docker build -t filefetcher .
# RUN-USING:    docker run --detach=true --name filefetcher filefetcher
#

# can't use onbuild due to SSL visibility
FROM python:3.7

RUN apt-get update && apt-get -y install cron

WORKDIR /root/.pip
ADD support/pip.conf .

WORKDIR /root/certs
add support/DOIRootCA2.cer .

WORKDIR /usr/share/ca-certificates/extra
ADD support/DOIRootCA2.cer DOIRootCA2.crt
RUN echo "extra/DOIRootCA2.crt" >> /etc/ca-certificates.conf && update-ca-certificates

WORKDIR /app/camfetcher
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt # 1

ADD VERSION .
ADD camfetcher.py .
RUN chmod 755 camfetcher.py
ADD support/cron-camfetcher .
ADD support/run_crond.sh  .
RUN chmod 755 run_crond.sh

CMD ["/app/camfetcher/run_crond.sh"]
