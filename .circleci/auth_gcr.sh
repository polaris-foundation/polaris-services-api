#!/usr/bin/env bash

set -eux

# Set up GCR auth
echo ${GOOGLE_AUTH} > ${HOME}/gcloud-service-key.json
gcloud --quiet auth activate-service-account ${SERVICE_ACCOUNT_ID} --key-file ${HOME}/gcloud-service-key.json
gcloud --quiet auth configure-docker
gcloud --quiet config set project ${GCP_PROJECT}
gcloud --quiet config set compute/zone ${GCP_COMPUTE_ZONE}
