# Use the official Ubuntu 22.04 (Jammy) as the base image
FROM ubuntu:22.04

# Set environment variables to avoid user interaction during package installation
ENV DEBIAN_FRONTEND=noninteractive
ARG USERNAME=llama
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN getent group $USER_GID 2>&1 >/dev/null || groupadd --gid $USER_GID $USERNAME 
RUN getent passwd $USER_UID 2>&1 >/dev/null || useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME \
  && apt-get update \
  && apt-get install -y sudo \
  && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME\
  && chmod 0440 /etc/sudoers.d/$USERNAME

# Update the package list and install necessary packages
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    sudo \
    git-all \
    curl \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    python-is-python3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

#RUN apt-get install -y curl
# Set Python 3.12 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

ARG YOUR_ENV

ENV YOUR_ENV=${YOUR_ENV} \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  # Poetry's configuration:
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR=/workspace/.cache/pypoetry \
  POETRY_HOME='/usr/local' \
  POETRY_VERSION=1.8.3

#Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
#ENV PATH "/home/$USERNAME/.local/bin:$PATH"
# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

#RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["python3", "app.py"]