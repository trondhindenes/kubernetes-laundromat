FROM ubuntu
RUN apt-get update \
    && apt-get install -y wget python3 curl \
    && curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py" \
    && apt-get remove --purge -y curl \
    && apt-get -y autoremove \
    && rm -rf /var/lib/apt/lists/*
RUN python3 get-pip.py
RUN pip install kubernetes==3.0.0
WORKDIR /app
COPY . /app
CMD ["python3", "-u", "laundromat.py"]%