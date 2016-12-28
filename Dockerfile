FROM python:3.4.5-wheezy

RUN apt-get update && \
    apt-get install -y numactl && \
    rm -rf /var/lib/apt/lists/*

ADD . /kcm
WORKDIR /kcm

RUN pip install -r requirements.txt && chmod +x /kcm/kcm.py

RUN tox -e lint
RUN tox -e unit
RUN tox -e integration

RUN /kcm/kcm.py --help && echo ""

ENTRYPOINT [ "/kcm/kcm.py" ]
