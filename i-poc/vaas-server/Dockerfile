# docker image for running Veracruz VaaS server
#
# AUTHORS
#
# The Veracruz Development Team.
#
# COPYRIGHT
#
# See the `LICENSE.markdown` file in the Veracruz I-PoC directory for licensing
# and copyright information.
#

FROM ubuntu:22.04

RUN apt-get update -y;apt-get upgrade -y;apt-get install -y curl python3-pip;apt-get -y clean

RUN pip3 install flask kubernetes jsonschema

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl";install -o root -g root -m 0755 kubectl /usr/bin/kubectl;rm kubectl

WORKDIR /root

COPY . /root

CMD /root/vaas-server.sh
