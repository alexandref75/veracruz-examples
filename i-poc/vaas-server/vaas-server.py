#!/usr/bin/env python3
#
# Implements VaaS server
# Instantiate Veracruz nitro instances and return valid policy with entrypoint
# Implements REST API (CRD)
#
# AUTHORS
#
# The Veracruz Development Team.
#
# COPYRIGHT AND LICENSING
#
# See the `LICENSING.markdown` file in the Veracruz I-PoC
# licensing and copyright information.


from flask import Flask,request,abort
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import json
import time
import jsonschema

def get_kubecon():
    try:
        config.load_incluster_config()
    except config.ConfigException as e:
        print("Kubernetes incluster configuration did not work",flush=True)
        try:
            config.load_kube_config()
        except config.ConfigException as e:
            print("Kubernetes kubeconfig configuration did not work",flush=True)
            return None

    try:
        kubecon = client.CoreV1Api()
    except ApiException as e:
        print("Kubernetes client access did not work err:"+str(e),flush=True)
        return None
        
    return kubecon

app = Flask(__name__)

@app.route('/veracruz/<name>', methods=['GET'])
def get_veracruz(name):
    print("Received veracruz get for name="+name,flush=True)
    error = None
    if request.method != 'GET':
        print("Received something different than GET",flush=True)
        return "<p>Not supported!</p>",400

    # get pod name = first portion of hostname + port#
    veracruzPodHost = name.split(":")

    if len(veracruzPodHost) != 2:
        return "<p>name should be on the form <host>:<port></p>"
 
    veracruzPod = veracruzPodHost[0].split(".")[0]+"-"+veracruzPodHost[1]

    kubeConnection = get_kubecon()
    if kubeConnection is None:
        return "<p>Error accessing K8s/kl3s</p>",500

    try:
        veracruzPodStatus = kubeConnection.read_namespaced_pod_status(veracruzPod,"default")
    except ApiException as e:
        print("Exception when calling read_namespaced_pod_status: %s\n" % e,flush=True)
        return "<p>Veracruz instance '"+name+"' does not existe!</p>",404
    except Exception as e:
        print("Exception when calling read_namespaced_pod_status: %s\n" % e,flush=True)
        return "<p>Error accessing k8s "+str(e)+"</p>",500

    return "<p>Veracruz instance '"+name+"' is running</p>"

@app.route('/veracruz/<name>', methods=['DELETE'])
def delete_veracruz(name):
    print("Received veracruz delete for name"+name,flush=True)
    error = None
    if request.method != 'DELETE':
        print("Received something different than DELETE",flush=True)
        return "<p>Not supported!</p>",400

    # get pod name = first portion of hostname + port#
    veracruzPodHost = name.split(":")

    if len(veracruzPodHost) != 2:
        return "<pname should be on the form <host>:<port></p>"
 
    veracruzPod = veracruzPodHost[0].split(".")[0]+"-"+veracruzPodHost[1]

    kubeConnection = get_kubecon()
    if kubeConnection is None:
        return "<p>Error accessing K8s/kl3s</p>",500

    try:
        veracruzPodDelete = kubeConnection.delete_namespaced_pod(veracruzPod,"default")
    except ApiException as e:
        print("Exception when calling delete_namespaced_pod: %s\n" % e,flush=True)
        return "<p>Veracruz instance '"+name+"' does not existe!</p>",404
    except Exception as e:
        print("Exception when calling read_namespaced_pod_status: %s\n" % e,flush=True)
        return "<p>Error accessing k8s "+str(e)+"</p>",500

    return "<p>Veracruz instance '"+name+"' was removed</p>"

@app.route("/veracruz", methods=['POST'])
def post_veracruz(): # create
    print("Received veracruz create",flush=True)
    error = None
    if request.method != 'POST':
        print("Received something different than POST",flush=True)
        return "<p>Not supported!</p>",400
    if not request.is_json:
        print("Received something different than json data",flush=True)
        return "<p>input should a json object!</p>",400

    requestJson = request.get_json()

    json_file_rights_schema = {
        "type": "array",
        "items" : {
            "type": "object",
            "properties": {
                 "file_name": { "type": "string"},
                 "rights": { "type": "integer"},
            },
            "additionalProperties": False
        },
        "additionalProperties": False
    }

    json_identity_schema = {
        "type": "array",
        "items" : {
            "type": "object",
            "properties": {
                 "certificate": { "type": "string"},
                 "file_rights": json_file_rights_schema,
                 "id": { "type":"integer" },
            },
            "required": ["certificate","file_rights","id"],
            "additionalProperties": False
        },
        "additionalProperties": False
    }

    json_program_schema = {
        "type": "array",
        "items" : {
             "type": "object",
             "properties": {
                 "file_rights": json_file_rights_schema,
                 "id": { "type":"integer" },
                 "pi_hash":  { "type":"string" },
                 "program_file_name":  { "type":"string" },
             },
             "required": ["file_rights","id","pi_hash","program_file_name"],
             "additionalProperties": False
        },
        "additionalProperties": False
    }

    json_policy_input_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "ciphersuite": { "type": "string"},
            "debug": { "type": "boolean"},
            "enable_clock": { "type": "boolean"},
            "execution_strategy": { "type": "string"},
            "identities": json_identity_schema,
            "programs":  json_program_schema,
        },
        "required": ["ciphersuite","debug","enable_clock","execution_strategy","identities","programs"],
        "additionalProperties": False
    }

    print("Checking if json is correct",flush=True)
    try:
        jsonschema.validate(instance=requestJson, schema=json_policy_input_schema)
    except jsonschema.exceptions.ValidationError as err:
        print("Received incorrect json data",flush=True)
        return "<p>Json object is not correct "+str(err)+"</p>",400


    print("Json is correct",flush=True)

    print("Processing create veraqcruz",flush=True)

    policy = requestJson;

    policy["ciphersuite"] = "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256"
    policy["enclave_cert_expiry"] = {
        "day": 23,
        "hour": 23,
        "minute": 44,
        "month": 12,
        "year": 2021
    }
    policy["proxy_attestation_server_url"]=os.environ['PROXY_ENDPOINT'] 
    policy["proxy_service_cert"]=os.environ['PROXY_CERTIFICATE'] 
    policy["runtime_manager_hash_nitro"]=os.environ['RUNTIME_MANAGER_HASH_NITRO'] 
    policy["runtime_manager_hash_sgx"]= ""
    policy["runtime_manager_hash_tz"]= ""
    policy["std_streams_table"]= [
        {
            "Stdin": {
                "file_name": "stdin",
                "rights": 8198
            }
        },
        {
            "Stdout": {
                "file_name": "stdout",
                "rights": 533572
            }
        },
        {
            "Stderr": {
                "file_name": "stderr",
                "rights": 533572
            }
        }
    ]

    kubeConnection = get_kubecon()
    if kubeConnection is None:
        return "<p>Error accessing K8s/kl3s</p>",500

    for veracruzport in range(int(os.environ['VERACRUZ_PORT_MIN']),int(os.environ['VERACRUZ_PORT_MAX'])+1):
        print("Trying port "+str(veracruzport),flush=True)
       
        try:
            configmap  = kubeConnection.read_namespaced_config_map("veracruz-nitro-server-"+str(veracruzport),"default")
        except ApiException as e:
            if e.status != 404:
                print("Exception when calling AdmissionregistrationApi->get_api_group: %s\n" % e,flush=True)
                return "<p>internal error '"+str(e)+"'!</p>"
            print("Port "+str(veracruzport)+" is not busy",flush=True)
            configMap = None
        except Exception as e:
            print("Exception when calling read_namespaced_config_map: %s\n" % e,flush=True)
            return "<p>Error accessing k8s "+str(e)+"</p>",500

        if not configMap is None:
            continue

        try:
            veracruzPod  = kubeConnection.read_namespaced_pod("veracruz-nitro-server-"+str(veracruzport),"default")
        except ApiException as e:
            if e.status != 404:
                print("Exception when calling AdmissionregistrationApi->get_api_group: %s\n" % e,flush=True)
                return "<p>internal error '"+str(e)+"'!</p>"
            print("Port "+str(veracruzport)+" is not busy",flush=True)
            veracruzPod = None
        except Exception as e:
            print("Exception when calling read_namespaced_config_map: %s\n" % e,flush=True)
            return "<p>Error accessing k8s "+str(e)+"</p>",500

        if veracruzPod is None:
            break

    if veracruzport >= int(os.environ['VERACRUZ_PORT_MAX'])+1:
        return "<p>no internal resources available!</p>",507
 
    print("Found this port open "+str(veracruzport),flush=True)
   
    policy["veracruz_server_url"] = os.environ['VERACRUZ_ENDPOINT_HOSTNAME']+":"+str(veracruzport)
    policy_str=str(json.dumps(policy, indent = 4))
    configMap = client.V1ConfigMap(
                     metadata = client.V1ObjectMeta(
                               name = "veracruz-nitro-server-"+str(veracruzport),
                               namespace = "default"
                     ),
                     data = {
                         "policy.json":policy_str
                         }
           )

    print("Creating configmap for port "+str(veracruzport),flush=True)
    try:
        configMapCreate = kubeConnection.create_namespaced_config_map("default",configMap)
    except ApiException as e:
        print("Exception when calling create_namespaced_config_map: %s\n" % e,flush=True)
        return "<p>Error accessing k8s "+str(e)+"</p>",500
    except Exception as e:
        print("Exception when calling create_namespaced_config_map: %s\n" % e,flush=True)
        return "<p>Error accessing k8s "+str(e)+"</p>",500

    print("Configmap created for port "+str(veracruzport),flush=True)

    print("Creating pod for port "+str(veracruzport),flush=True)
    veracruzPod = client.V1Pod(
                metadata = client.V1ObjectMeta(
                          name = "veracruz-nitro-server-"+str(veracruzport),
                          namespace = "default",
                          labels = { "veracruz-nitro":"server"}
                ),
                spec = client.V1PodSpec(
                          service_account_name = "default",
                          automount_service_account_token = False,
                          dns_policy = "ClusterFirstWithHostNet",
                          hostname = "veracruz-nitro-server",
                          containers = [
                                  client.V1Container(
                                          name = "veracruz-nitro-server",
                                          image_pull_policy = "IfNotPresent",
                                          #image = "alexandref75arm/veracruz-nitro:v0.7",
                                          image = os.environ['RUNTIME_MANAGER_IMAGE'],
                                          command = ["/bin/bash",
                                                "-c",
                                                "echo -e $(grep veracruz-nitro-server /etc/hosts | cut -f 1)\"\t"+os.environ['VERACRUZ_ENDPOINT_HOSTNAME']+"\" >> /etc/hosts;exec /work/veracruz-server/veracruz-server /work/veracruz-server-policy/policy.json"
                                          ],
                                          ports = [
                                                client.V1ContainerPort(
                                                          container_port = veracruzport,
                                                          protocol = "TCP",
                                                          name = "veracruz-"+str(veracruzport)
                                                )
                                          ],
                                          resources = client.V1ResourceRequirements(
                                                  limits = {
                                                          "smarter-devices/nitro_enclaves": "1",
                                                          "smarter-devices/vsock": "1",
                                                          "hugepages-2Mi": "512Mi",
                                                          "memory": "2Gi",
                                                          "cpu": "250m"
                                                  },
                                                  requests = {
                                                          "smarter-devices/nitro_enclaves": "1",
                                                          "smarter-devices/vsock": "1",
                                                          "hugepages-2Mi": "512Mi",
                                                          "cpu": "10m",
                                                          "memory": "100Mi"
                                                  }
                                          ),
                                          volume_mounts = [
                                                  client.V1VolumeMount(
                                                        mount_path = "/dev/hugepages",
                                                        name = "hugepage",
                                                        read_only = False),
                                                  client.V1VolumeMount(
                                                        mount_path = "/work/veracruz-server-policy",
                                                        name = "config"),
                                                  client.V1VolumeMount(
                                                        mount_path = "/run/nitro_enclaves",
                                                        name = "run-enclaves"),
                                                  client.V1VolumeMount(
                                                        mount_path = "/var/log/nitro_enclaves",
                                                        name = "nitro-enclaves")
                                          ]

                                  )
                          ],
                          volumes = [
                                  client.V1Volume(
                                          name = "hugepage",
                                          empty_dir = client.V1EmptyDirVolumeSource(
                                                  medium = "HugePages")
                                  ),
                                  client.V1Volume(
                                          name = "config",
                                          config_map = client.V1ConfigMapVolumeSource(
                                                  name = "veracruz-nitro-server-"+str(veracruzport))
                                  ),
                                  client.V1Volume(
                                          name = "run-enclaves",
                                          host_path = client.V1HostPathVolumeSource(
                                                  path = "/run/nitro_enclaves")
                                  ),
                                  client.V1Volume(
                                          name = "nitro-enclaves",
                                          host_path = client.V1HostPathVolumeSource(
                                                  path = "/var/log/nitro_enclaves")
                                  )
                          ]
                )
      )

    try:
        veracruzPodCreated = kubeConnection.create_namespaced_pod("default",veracruzPod)
    except ApiException as e:
        print("Exception when calling create_namespaced_pod: %s\n" % e,flush=True)
        configMapCreate = kubeConnection.delete_namespaced_config_map("veracruz-nitro-server-"+str(veracruzport),"default")
        return "<p>Could not create a veracruz instance!</p>",500
    except Exception as e:
        print("Exception when calling delete_namespaced_config_map: %s\n" % e,flush=True)
        return "<p>Error accessing k8s "+str(e)+"</p>",500

    print("Pod created for port "+str(veracruzport),flush=True)

    print("Checking IP for Pod for port "+str(veracruzport),flush=True)
    veracruzPodIP = None
    for i in range(20):
        try:
            veracruzPodStatus = kubeConnection.read_namespaced_pod_status("veracruz-nitro-server-"+str(veracruzport),"default")
        except ApiException as e:
            print("Exception when calling read_namespaced_pod_status: %s\n" % e,flush=True)
            veracruzPodStatus = kubeConnection.delete_namespaced_pod("veracruz-nitro-server-"+str(veracruzport),"default")
            configMapCreate = kubeConnection.delete_namespaced_config_map("veracruz-nitro-server-"+str(veracruzport),"default")
            return "<p>Could not get status for veracruz instance!</p>",500

        veracruzPodIP = veracruzPodStatus.status.pod_ip
        if not veracruzPodIP is None:
            break

        print("Veracruz pod status not set yet, waiting ",flush=True)

        time.sleep(1)


    if veracruzPodIP is None:
        print("IP not available after 20s for Pod for port "+str(veracruzport),flush=True)
        veracruzPodStatus = kubeConnection.delete_namespaced_pod("veracruz-nitro-server-"+str(veracruzport),"default")
        configMapCreate = kubeConnection.delete_namespaced_config_map("veracruz-nitro-server-"+str(veracruzport),"default")
        return "<p>Could not get status for veracruz instance!</p>",500

    print("Found IP address for pod "+veracruzPodIP,flush=True)

    veracruzEndpointSlice = client.V1beta1EndpointSlice(
                metadata = client.V1ObjectMeta(
                          name = "veracruz-nitro-server-"+str(veracruzport),
                          namespace = "default",
                          labels = { "kubernetes.io/service-name":"veracruz-nitro-server"}
                ),
                address_type = "IPv4",
                ports = [
                    client.V1beta1EndpointPort(
                        protocol = "TCP",
                        port = veracruzport, 
                        name = "veracruz-"+str(veracruzport)
                    )
                ],
                endpoints = [
                    client.V1beta1Endpoint(
                        addresses = [
                            veracruzPodIP
                        ],
                        conditions = client.V1beta1EndpointConditions(
                            ready = True
                        )
                    )
                ]
            )

    kubeConnectionBeta = client.DiscoveryV1beta1Api()
    try:
        veracruzEndpointSliceCreated = kubeConnectionBeta.create_namespaced_endpoint_slice("default",veracruzEndpointSlice)
    except ApiException as e:
        print("Exception when calling create_namespaced_endpoint_slice: %s\n" % e,flush=True)
        veracruzPodStatus = kubeConnection.delete_namespaced_pod("veracruz-nitro-server-"+str(veracruzport),"default")
        configMapCreate = kubeConnection.delete_namespaced_config_map("veracruz-nitro-server-"+str(veracruzport),"default")
        return "<p>Could not create the networking configuration for veracruz instance!</p>",500

    policy_file = open("policy-veracruz-nitro-server-"+str(veracruzport),"w")
    policy_file.write(str(json.dumps(policy, indent = 4)))
    policy_file.close()

    return {"policy":policy_str}
