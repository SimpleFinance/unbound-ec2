FROM centos:7

RUN yum clean all \
    && yum -y install epel-release \
    && yum -y install unbound python python-setuptools unbound-python python-pip bind-utils

RUN pip install boto

EXPOSE 53/udp

ADD . /application

WORKDIR /application
RUN rm -rf dist/ && python setup.py build sdist && find dist -type f -name "*.tar.gz" -exec pip install {} \;

VOLUME /etc/unbound

ENTRYPOINT ["unbound"]
CMD ["-d"]