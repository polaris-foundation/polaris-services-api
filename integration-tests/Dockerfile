FROM python:3.9-slim

WORKDIR /app
ARG PIP_EXTRA_INDEX_URL

# Install dependencies
ADD requirements.txt .
RUN apt-get update \
    && apt install openssh-client sshpass -y \
    && pip install -r requirements.txt

# Add the app
ADD . .

# Go go go (overridden in docker-compose.yaml)
CMD ["behave", "--no-capture"]
