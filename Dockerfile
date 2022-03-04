FROM python:3.9-slim-buster as build-image

ENV IN_DOCKER Yes

ARG FUNCTION_DIR=/code
RUN mkdir -p ${FUNCTION_DIR}
WORKDIR ${FUNCTION_DIR}

COPY src/requirements.txt ${FUNCTION_DIR}/src/requirements.txt
RUN pip install -r src/requirements.txt

COPY . ${FUNCTION_DIR}

WORKDIR ${FUNCTION_DIR}/src
CMD python bot.py
