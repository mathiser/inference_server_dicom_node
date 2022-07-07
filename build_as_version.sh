#!/bin/bash
if [ "$#" -ne 1 ]; then
    echo "Arg must be a version string - e.g.: 1.2.3"
    exit 1
fi

docker build . -t mathiser/inference_server_dicom_node:v$1
docker push mathiser/inference_server_dicom_node:v$1

