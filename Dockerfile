FROM pandoc/core:2.19.2

RUN apk add python3 py3-pip
RUN pip3 install --upgrade pip
RUN pip3 install requests pandoc

COPY wiki_to_adoc.py /usr/local/bin/wiki_to_adoc
WORKDIR /data
ENTRYPOINT ["wiki_to_adoc"]
