#!/bin/bash

docker network inspect ki-enterprise >/dev/null 2>&1

if [ $? -ne 0 ]; then
    docker network create \
        --driver bridge \
        ki-enterprise

    echo "Network oluşturuldu."
else
    echo "Network zaten mevcut."
fi
