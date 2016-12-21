FROM python:3.4.5-wheezy

ADD . /kcm
WORKDIR /kcm
RUN pip install -r requirements.txt
RUN tox -e lint
RUN tox -e unit
CMD [ "python", "/kcm/intel/kcm.py" ]
