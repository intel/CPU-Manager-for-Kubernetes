FROM python:3.4.5-wheezy

ADD . /kcm
WORKDIR /kcm

RUN pip install -r requirements.txt && chmod +x /kcm/kcm.py

ENTRYPOINT [ "/kcm/kcm.py" ]
