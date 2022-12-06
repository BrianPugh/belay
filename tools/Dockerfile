FROM ubuntu:latest

ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    nodejs \
    npm \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Install RP2040 emulator
RUN cd / \
    && git clone https://github.com/BrianPugh/rp2040js.git \
    && cd rp2040js \
    && curl -OJ https://micropython.org/resources/firmware/rp2-pico-20210902-v1.17.uf2 \
    && git checkout check-tty \
    && npm install

WORKDIR /belay

# To ignore a possibly existing ".venv" folder in the mapped volume.
RUN poetry config virtualenvs.in-project false
