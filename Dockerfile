FROM python:3.12-slim-bullseye AS builder

RUN pip install poetry==2.1.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN touch README.md

# Install dependencies with caching enabled
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --no-root --only=main

FROM python:3.12-slim-bullseye AS runtime

RUN useradd --create-home appuser

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder --chown=appuser:appuser ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY --chown=appuser:appuser app/src ./

USER appuser

# Default command
CMD python main.py