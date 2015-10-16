FROM ubuntu:14.04
MAINTAINER Alexandr Kostrikov <akostrikov@mirantis.com>
RUN apt-get update && apt-get install --force-yes -qq curl git python2.7 python-dev build-essential lib32z1-dev libxml2-dev libxslt-dev createrepo
RUN update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
RUN curl https://bootstrap.pypa.io/get-pip.py|python
# cd /tmp && git clone --depth 1 https://github.com/bgaifullin/packetary.git && pip install packetary/
# docker build -t packetary/tester .
# docker run --rm -i -t packetary/tester /bin/bash
# packetary mirror -t yum -u "http://mirror.yandex.ru/centos/6.7/os" -r "http://mirror.fuel-infra.org/mos-repos/centos/mos8.0-centos6-fuel/os" -d /tmp/mirror/centos
# packetary mirror -u "https://raw.githubusercontent.com/akostrikov/provides/master/dists mos8.0 main" -r "https://raw.githubusercontent.com/akostrikov/needs/master/dists/ mos8.0 main" -d /tmp/mirror/ubuntu

