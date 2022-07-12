#!/bin/bash
SERVER_PORT=${1-5000}
export SERVER_PORT=${SERVER_PORT}
export NEO4J_DB_URL=localhost
export NEO4J_DB_PORT=${NEO4J_DB_PORT:=7687}
export NEO4J_DB_USERNAME=neo4j
export NEO4J_DB_PASSWORD=TopSecretPassword
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_USER=dhos-services-api
export DATABASE_PASSWORD=dhos-services-api
export DATABASE_NAME=dhos-services-api
export FLASK_APP=dhos_services_api/autoapp.py
export ENVIRONMENT=DEVELOPMENT
export ALLOW_DROP_DATA=true
export IGNORE_JWT_VALIDATION=true
export AUTH0_DOMAIN=https://login-sandbox.sensynehealth.com/
export AUTH0_AUDIENCE=https://dev.sensynehealth.com/
export AUTH0_METADATA=https://gdm.sensynehealth.com/metadata
export AUTH0_JWKS_URL=https://login-sandbox.sensynehealth.com/.well-known/jwks.json
export HS_KEY=secret
export PROXY_URL=http://localhost
export AUTH0_CUSTOM_DOMAIN=dev
export RABBITMQ_DISABLED=true
export CUSTOMER_CODE=DEV
export REDIS_INSTALLED=False
export LOG_LEVEL=DEBUG
export LOG_FORMAT=${LOG_FORMAT:-COLOUR}
export DHOS_USERS_API_HOST=http://localhost:5001

if [ -z "$*" ]
then
  flask db upgrade
  python3 -m dhos_services_api
else
  python3 -m flask $*
fi
