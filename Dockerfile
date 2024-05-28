FROM python:3.9-slim-buster as build-image

ENV IN_DOCKER Yes

ARG FUNCTION_DIR=/code
RUN mkdir -p ${FUNCTION_DIR}
WORKDIR ${FUNCTION_DIR}

COPY src/requirements.txt ${FUNCTION_DIR}/src/requirements.txt
RUN pip install -r src/requirements.txt

COPY . ${FUNCTION_DIR}

# Copy UYA SSH private key into container. Added || true so that this isn't required
RUN mkdir -p /root/.ssh/
RUN chmod 700 /root/.ssh/
RUN cp ${FUNCTION_DIR}/ssh_keys/* /root/.ssh/ || true
RUN chmod 600 /root/.ssh/* || true

WORKDIR ${FUNCTION_DIR}/src
CMD python -u bot.py
