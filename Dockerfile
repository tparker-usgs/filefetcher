# pull daily files

# can't use onbuild due to SSL visibility
FROM python:3.7

WORKDIR /root/certs
add support/DOIRootCA2.cer .

WORKDIR /usr/share/ca-certificates/extra
ADD support/DOIRootCA2.cer DOIRootCA2.crt
RUN echo "extra/DOIRootCA2.crt" >> /etc/ca-certificates.conf && update-ca-certificates

ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.1.6/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=c3b78d342e5413ad39092fd3cfc083a85f5e2b75

RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

WORKDIR /app/filefetcher
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt # 1

ENV CONFIG_UPDATER_CONFIG=/tmp/configupdater.yaml
ADD VERSION .
ADD support/cron-filefetcher .
ADD filefetcher.py .
RUN chmod 755 *.py

CMD ["/usr/local/bin/supercronic","/app/filefetcher/cron-filefetcher"]
