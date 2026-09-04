ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
FROM ${PYTHON_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_DEFAULT_TIMEOUT=120

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
