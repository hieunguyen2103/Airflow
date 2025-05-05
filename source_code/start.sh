#!/bin/bash
sudo docker volume prune -f

sudo docker-compose run --rm airflow-webserver airflow db init

sudo docker-compose run --rm airflow-webserver airflow users create \
  --username admin \
  --password admin \
  --firstname Hieu \
  --lastname Nguyen \
  --role Admin \
  --email hsku2009@gmail.com

sudo docker-compose up -d
