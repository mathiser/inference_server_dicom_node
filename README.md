# inference_server_dicom_node
This InferenceServerDicomNode (IS-DN) is setup to to serve (InferenceServer)[https://github.com/mathiser/inference_server] through regular dicom networking protocols.
The supported workflow is as follows:
## Flow through ISDN
### The Store SCP (src/scp/scp.py)
- A SCP receives scans with regular dicom networking C_STORE events. 
- Incoming dicom files are sorted out in a folder structure of /patient_id/study_description/modality
### The InferenceServer post daemon (src/daemons/inference_server_daemon.py)
- The post daemon runs with a fixed interval (default is 1 sec) and checks timestamp of all incoming folders (/patient_id/study_description/modality).
- If a folder is untouched for a specified interval of time (default is 10 sec.), the folder checked via the DB for 
matching fingerprints. A fingerprint is a specification file which contains information on which modalities and keywords
in series descriptions that should trigger which model on which InferenceServer endpoint - and subsequently which dicom 
node the predictions should be send to (usually PACS or TPS, by can be any Store SCP)

### The InferenceServer get-thread (src/daemons/get_thread.py)
This is a thread that is initialized when a job is posted with the post daemon.
- It polls InferenceServer with a fixed interval of time to check whether the job is finished. If a task fails on the server, the get_thread will terminate.
- When the InferenceServer has the predictions ready, they are send to the get_thread, which in turn ships the result on to the Store SCP specified in the fingerprint file.

## How-to's
### Set up configurations
IS-DN is meant to run in a docker container. You must bind the following folder structure into the container:
CONFIGURATION
  |-CERTS/cert.crt
  |-FINGERPRINTS
  |  |-fingerprint1.json
  |  |-fingerprint2.json
  |-SCP
  |  |-scp.json

CONFIGURATION/CERTS/cert.crt is the public key to the TLS of InferenceServers. Multiple certs can be merged into this file.
See CONFIGURATION/FINGERPRINTS/fingerprint.json.example for an example on how to configure a fingerprint
See CONFIGURATION/SCP/scp.json.example for example on how to configure the SCP.

### Run in docker
Assuming that the project is build (see /build.sh as example on howto), you can run IS-DN with 
```shell
docker run \
  -d \
  -it \
  --restart=always \
  --network=host \
  --volume /absolute/path/to/CONFIGURATION:/CONFIGURATION \
  --name dicom_node \
  mathiser/inference_server_dicom_node:v0.2.1
```
... or you can adabt and run `run.sh.example`

### Attach to the logs
You can attach to the docker logs with:
`docker logs -f dicom_node`

### Restart IS-DN
Can you have updated something in CONFIGURATION, you need to restart IS-DN:
`docker restart dicom_node`

### Hard restart IS-DN
If everything is wrong or you want to upgrade to a newer version:
`docker stop dicom_node && docker rm dicom_node`

### Update to another build of IS-DN
```
docker stop dicom_node && docker rm dicom_node
docker pull mathiser/inference_server_dicom_node:some_other_tag
docker run \
  -d \
  -it \
  --restart=always \
  --network=host \
  --volume /absolute/path/to/CONFIGURATION:/CONFIGURATION \
  --name dicom_node \
  mathiser/inference_server_dicom_node:some_other_tag
```

