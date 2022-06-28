#!/bin/bash
if [ "$#" -ne 2 ]; then
    echo "Illegal number of parameters"
    exit 1
fi


docker run \
  -it \
  -d \
  --restart=always \
  --network=host \
  --volume $(realpath $1):/DICOM_ENDPOINTS \
  --volume $(realpath $2):/CERTS \
  --name dicom_node_scp \
  mathiser/inference_server_dicom_node:v0.1
