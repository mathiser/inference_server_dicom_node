#!/bin/bash
docker rm -f dicom_node
docker run \
  -d \
  -it \
  --restart=always \
  --network=host \
  --volume $(realpath mount/cert.crt):/opt/app/cert.crt \
  --volume $(realpath mount/DICOM):/opt/app/DICOM \
  --volume $(realpath mount/database):/opt/app/database \
  --name dicom_node \
     mathiser/inference_server_dicom_node:dev
