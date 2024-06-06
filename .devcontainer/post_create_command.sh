#!/bin/bash

cd web && npm install

echo 'alias start-api="cd /workspaces/dify/api && flask run --host 0.0.0.0 --port=5001 --debug"' >> ~/.bashrc
echo 'alias start-worker="cd /workspaces/dify/api && celery -A app.celery worker -P gevent -c 1 --loglevel INFO -Q dataset,generation,mail"' >> ~/.bashrc
echo 'alias start-web="cd /workspaces/dify/web && npm run dev"' >> ~/.bashrc
echo 'alias start-containers="cd /workspaces/dify/docker && docker-compose -f docker-compose.middleware.yaml -p dify up -d"' >> ~/.bashrc

source /home/vscode/.bashrc