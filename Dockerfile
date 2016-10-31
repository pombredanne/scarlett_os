FROM  bossjones/boss-docker-jhbuild-pygobject3:v1
MAINTAINER Malcolm Jones <bossjones@theblacktonystark.com>

COPY ./ /home/pi/dev/bossjones-github/scarlett_os

WORKDIR /home/pi/dev/bossjones-github/scarlett_os

RUN set -x cd /home/pi/dev/bossjones-github/scarlett_os \
    && pwd \
    && jhbuild run -- pip install -r requirements.txt \
    && jhbuild run python3 setup.py install \
    && jhbuild run -- pip install -e .[test]

COPY ./container/root /

ENTRYPOINT ["/docker_entrypoint.sh"]
CMD true
