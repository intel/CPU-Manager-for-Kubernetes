FROM python:3.4.5-wheezy

ADD . /kcm
WORKDIR /kcm

RUN pip install -r requirements.txt

RUN tox -e lint
RUN tox -e unit
# RUN tox -e integration

RUN chmod +x /kcm/kcm.py && /kcm/kcm.py --help && echo ""

ENTRYPOINT [ "/kcm/kcm.py" ]
