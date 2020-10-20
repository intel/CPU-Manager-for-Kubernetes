FROM clearlinux/python:3.8.6

RUN swupd bundle-add c-basic

COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

COPY . /cmk
WORKDIR /cmk

RUN chmod +x /cmk/cmk.py

RUN /cmk/cmk.py --help && echo

CMD ["/cmk/cmk.py" ]
