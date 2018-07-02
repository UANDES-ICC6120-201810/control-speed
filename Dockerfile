# For ARM architectures use
FROM arm32v7/ubuntu:latest

# For x86 architectures use
# FROM ubuntu:latest

ARG DEBIAN_FRONTEND=noninteractive

# Install dependencies
# Important to keep the '-y' to say 'yes' to the prompt or will raise non-zero error.

RUN apt-get update \
    && apt-get install -y python2.7 \
                          python-pip \
                          nano \
# Doesn't work... needs user input
                          python-opencv \
    && pip install mysql-connector \
                   requests

CMD python /root/speed-script.py
