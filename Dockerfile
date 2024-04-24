FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        sudo \
        vim \ 
        apt-transport-https \ 
        ca-certificates \ 
        gnupg \
        curl \
        make \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Google Cloud
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get update && sudo apt-get install google-cloud-cli

ENV MINICONDA_VERSION=latest
RUN curl -sL "https://repo.anaconda.com/miniconda/Miniconda3-${MINICONDA_VERSION}-Linux-x86_64.sh" -o /miniconda.sh && \
    bash /miniconda.sh -b -p /miniconda && \
    rm /miniconda.sh

ENV PATH=/miniconda/bin:${PATH}

RUN conda install -y python=3.11 && \
    conda clean -afy

WORKDIR /app

COPY . .

RUN pip3 install -e .

EXPOSE 8080

# CMD ["uvicorn", "gen_ai.deploy.api:app", "--reload", "--port", "8080"]
# CMD uvicorn gen_ai.deploy.api:app --reload --host 0.0.0.0 --port $PORT
