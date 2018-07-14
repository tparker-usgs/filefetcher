# pull GPS files
#
# BUILD-USING:  docker build -t gpspull .
# RUN-USING:    docker run --detach=true --name gpspull gpspull
#

# can't use onbuild due to SSL visibility
FROM python:3.7

RUN apt-get update && apt-get -y install cron

WORKDIR /root/.pip
ADD pip.conf .

WORKDIR /root/certs
add DOIRootCA2.cer .

WORKDIR /usr/share/ca-certificates/extra
ADD DOIRootCA2.cer DOIRootCA2.crt
RUN echo "extra/DOIRootCA2.crt" >> /etc/ca-certificates.conf && update-ca-certificates

WORKDIR /app/gpspull
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt # 1

ADD VERSION .
ADD gpspull.py .
RUN chmod 755 gpspull.py
ADD cron-gpspull .
ADD run_crond.sh  .
RUN chmod 755 run_crond.sh

CMD ["/app/gpspull/run_crond.sh"]
