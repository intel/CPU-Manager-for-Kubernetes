FROM python:3.4.5-wheezy

ADD . /kcm
WORKDIR /kcm

RUN pip install -r requirements.txt && chmod +x /kcm/kcm.py

RUN tox -e lint
RUN tox -e unit
RUN tox -e integration
RUN tox -e coverage

RUN /kcm/kcm.py --help && echo ""

ENTRYPOINT [ "/kcm/kcm.py" ]
