#!/bin/bash
docker run \
  -d \
  -it \
  --restart=always \
  --network=host \
  --volume $(realpath CONFIGURATION):/CONFIGURATION \
  --name dicom_node \
  -e SCP_HOSTNAME=localhost \
  -e SCP_PORT=11113 \
  -e SCP_AE_TITLE=DL_pipe \
  -e ASK_INFERENCE_SERVER_TO_DELETE_TASK="" \
     mathiser/inference_server_dicom_node:dev
