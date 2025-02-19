#!/bin/bash
# Start VaaS server using flask
#
# AUTHORS
#
# The Veracruz Development Team.
#
# COPYRIGHT AND LICENSING
#
# See the `LICENSE_MIT.markdown` file in the Veracruz I-PoC
# example repository root directory for copyright and licensing information.
#!/bin/bash

if [ -z "${PROXY_ENDPOINT}" -o -z "${PROXY_CERTIFICATE}" -o -z "${RUNTIME_MANAGER_HASH_NITRO}" -o -z "${VERACRUZ_PORT_MIN}" -o -z "${VERACRUZ_PORT_MAX}" ]
then
     echo "Pleaset set the environment variables PROXY_ENDPOINT, PROXY_CERTIFICATE, RUNTIME_MANAGER_HASH_NITRO, VERACRUZ_PORT_MIN, VERACRUZ_PORT_MAX"
     exit 1
fi

nohup ./veracruz-clean-leftover-k8s-objects.sh&

export FLASK_APP=vaas-server
flask run --host=0.0.0.0
