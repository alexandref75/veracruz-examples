#!/usr/bin/env python3
#
# Implements the user side of the Iotex application
# Request an instance of the function from CCFaaS
# Requestg an instance of iotex-s3-app
# Read results from Veracruz instance
# Terminate instance when finished
#
# AUTHORS
#
# The Veracruz Development Team.
#
# COPYRIGHT AND LICENSING
#
# See the `LICENSING.markdown` file in the Veracruz I-PoC
# licensing and copyright information.


import requests
import os
import re
import json
import sys
import secrets
from OpenSSL import crypto, SSL
from socket import gethostname
from pprint import pprint
from time import gmtime, mktime

# openssl genrsa -out example/example-program-key.pem 2048
# openssl req -new -x509 -sha256 -nodes -days 3650 \
#    -key example/example-program-key.pem \
#    -out example/example-program-cert.pem \
#    -config test-collateral/cert.conf
# cert.conf
# [req]
# default_bits = 2048
# prompt = no
# default_md = sha256
# x509_extensions = v3_req
# distinguished_name = dn
# 
# [dn]
# C = Mx
# ST = Veracruz
# L = Veracruz
# O = Zibble Zabble
# emailAddress = zibble@zabble.zibble
# CN = zibblezabble
# 
# [v3_req]
# subjectAltName = @alt_names
# 
# [alt_names]
# DNS.1 = zabble.zibble
# DNS.2 = www.zabble.zibble


def create_self_signed_cert():

    # create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA,2048)

    # create a self-signed cert
    cert = crypto.X509()
    cert.set_version(2)
    cert.get_subject().C = "Mx"
    cert.get_subject().ST = "Veracruz"
    cert.get_subject().L = "Veracruz"
    cert.get_subject().O = "Zibble Zabble"
    cert.get_subject().CN = "zibblezabble"
    cert.get_subject().emailAddress = "zibble@zabble.zibble"
    cert.add_extensions([
        crypto.X509Extension(b'subjectAltName',False,b'DNS.1:zabble.zibble,DNS.2:www.zabble.zibble')
        ])
    cert.set_serial_number(int.from_bytes(secrets.token_bytes(20),'big'))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    return [k,cert]

def certToStringVeracruz(certUse):
    certStr = re.sub('([^-])\n([^-])|\n$','\g<1>\g<2>',crypto.dump_certificate(crypto.FILETYPE_PEM, certUse).decode('utf-8'))
    return certStr

def keyToStringVeracruz(keyUse):
    keyStr = re.sub('([^-])\n([^-])|\n$','\g<1>\g<2>',crypto.dump_privatekey(crypto.FILETYPE_PEM, keyUse).decode('utf-8'))
    return keyStr

if __name__ == "__main__":
    if len(sys.argv) < 5:
       print(sys.argv[0]+": <uniqueID> <URL of CCFaaS> <URL of iotex-S3> <bucket of S3> <File in S3> <S3 authentication>")
       print("      S3 authentication is format <entry>=<value> where entries are: region_name, aws_access_key_id, aws_secret_access_key, aws_session_token")
       os._exit(1)

    uniqueID = sys.argv[1]
    ccfaasURL = sys.argv[2]
    iotexS3URL = sys.argv[3]
    s3_auth={ "bucket" : sys.argv[4],
         "filename" : sys.argv[5] }
    outputFile=sys.argv[5]+".output"

    entries = ["region_name", "aws_access_key_id", "aws_secret_access_key", "aws_session_token"]

    for i in range(6,len(sys.argv)):
        entry,value = sys.argv[i].split('=',1)
        if not entry in entries:
            print("entry=\""+entry+"\" not reecognied")
            os._exit(1)
        s3_auth[entry] = value

    USER_CERT_FILE = "USERcert.pem"
    USER_KEY_FILE = "USERkey.pem"
    S3_CERT_FILE = "S3cert_"+uniqueID+".pem"
    S3_KEY_FILE = "S3key_"+uniqueID+".pem"
     
    if os.path.exists(USER_CERT_FILE) and os.path.exists(USER_KEY_FILE):
        usercert = crypto.load_certificate(crypto.FILETYPE_PEM, open(USER_CERT_FILE, 'rb').read(-1))
        userk = crypto.load_privatekey(crypto.FILETYPE_PEM, open(USER_KEY_FILE, 'rb').read(-1))
        print("User certificate loaded from "+USER_CERT_FILE+" and key from "+USER_KEY_FILE)
    else:
        userk,usercert = create_self_signed_cert()
        open(USER_CERT_FILE, "wt").write(crypto.dump_certificate(crypto.FILETYPE_PEM, usercert).decode('utf-8'))
        open(USER_KEY_FILE, "wt").write(crypto.dump_privatekey(crypto.FILETYPE_PEM, userk).decode('utf-8'))
        print("User certificate created and saved on "+USER_CERT_FILE+" and key saved on "+USER_KEY_FILE)
     
    #s3cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(S3_CERT_FILE, 'rb').read(-1))
    #s3k = crypto.load_privatekey(crypto.FILETYPE_PEM, open(S3_KEY_FILE, 'rb').read(-1))

    s3k,s3cert = create_self_signed_cert()
    open(S3_CERT_FILE, "wt").write(crypto.dump_certificate(crypto.FILETYPE_PEM, s3cert).decode('utf-8'))
    open(S3_KEY_FILE, "wt").write(crypto.dump_privatekey(crypto.FILETYPE_PEM, s3k).decode('utf-8'))
    print("S3 certificate created")

    iotexAppRequestJson = {
       "function":"linear-regression",
       "instanceid": uniqueID,
       "identities": [
           {
               "certificate": certToStringVeracruz(s3cert),
               "file_rights": [
                   {
                       "file_name": "input-0",
                       "rights": 533572
                   }
               ]
           },
           {
               "certificate": certToStringVeracruz(usercert),
               "file_rights": [
                   {
                        "file_name": "output",
                        "rights": 8198
                    }
               ]
           }
       ]
    }
#    iotexAppRequestJson = {
#       "function":"linear-regression",
#       "instanceid": uniqueID,
#       "identities": [
#           {
#               "certificate": certToStringVeracruz(s3cert),
#               "file_rights": [
#                   {
#                       "file_name": "input-0",
#                       "rights": 533572
#                   },
#	           {
#	               "file_name": "output",
#	               "rights": 8198
#	           }
#               ]
#           }
#       ]
#    }

    print("Creating instance URL="+ccfaasURL+"/instance")
    
    try:
        iotexAppResponse = requests.post(ccfaasURL+"/instance",
                                headers = {"Content-Type":"application/json"},
                                data=json.dumps(iotexAppRequestJson, indent = 4))
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # Python 3.6
        os._exit(1)
    except Exception as err:
        print(f'Other error occurred: {err}')  # Python 3.6
        os._exit(1)
    
    if iotexAppResponse.status_code != 200:
        print("Http request to CCFaaS returned "+str(iotexAppResponse.status_code))  # Python 3.6
        os._exit(1)
    
    try:
        policy = iotexAppResponse.json()
    except JSONDecodeError as err:
        print("Http request to CCFaaS returned "+str(err))  # Python 3.6
        os._exit(1)
    
    print("Response = "+str(iotexAppResponse),flush=True)

    policy_filename = "policy_"+uniqueID

    print("Writing policy to "+policy_filename)

    policy_file = open(policy_filename,"w")
    policy_file.write(policy["policy"])
    policy_file.close()
    
    iotexS3AppRequestJson = {
        "s3" : s3_auth,
        "veracruz" : {
                "filename" : "input-0",
                "policy" : policy["policy"],
                "certificate" : certToStringVeracruz(s3cert),
                "key" : keyToStringVeracruz(s3k),
        }
    }

    print("Creating s3 app URL="+iotexS3URL+"/s3_stream_veracruz")

    try:
        iotexS3AppResponse = requests.post(iotexS3URL+"/s3_stream_veracruz",
                                headers = {"Content-Type":"application/json"},
                                data=json.dumps(iotexS3AppRequestJson, indent = 4))
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # Python 3.6
        os._exit(1)
    except Exception as err:
        print(f'Other error occurred: {err}')  # Python 3.6
        os._exit(1)
 
    if iotexS3AppResponse.status_code != 200:
        print("Http request to S3 app returned "+str(iotexS3AppResponse.status_code))  # Python 3.6
        os._exit(1)

    execute_string="./execute_program.sh "+policy_filename+" "+USER_CERT_FILE+" "+USER_KEY_FILE+"  linear-regression.wasm "+outputFile
    print("execute: "+execute_string,flush=True)
    if os.system(execute_string) != 0:
        print("execute retuned eror so cleaning up",flush=True)

    print("Deleting instance URL="+ccfaasURL+"/"+uniqueID)
    try:
        iotexAppResponse = requests.delete(ccfaasURL+"/"+uniqueID)
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # Python 3.6
        os._exit(1)
    except Exception as err:
        print(f'Other error occurred: {err}')  # Python 3.6
        os._exit(1)
    
    if iotexAppResponse.status_code != 200:
        print("Http request to CCFaaS returned "+str(iotexAppResponse.status_code))  # Python 3.6
        os._exit(1)
    
    os._exit(0)
    
