FROM python:3.9-alpine

RUN apk update && apk upgrade && \
    apk add --no-cache \
    alpine-sdk \
    linux-headers \
    git \
    zlib-dev \
    openssl-dev \
    gperf \
    php \
    cmake \
    make \
    g++

RUN git clone https://github.com/tdlib/td.git && \
    cd td && \
    rm -rf build && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=/usr/local .. && \
    cmake --build . --target install && \
    cd ../.. && \
    rm -rf td

WORKDIR /code

RUN apk add --no-cache libstdc++

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

CMD ["python", "src/main.py"]