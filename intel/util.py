# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import re
from base64 import b64encode
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from packaging.version import parse

from os.path import normpath, realpath, join, pardir


def cmk_root():
    return normpath(realpath(join(__file__, pardir, pardir)))


def ldh_convert_check(name):
    name_con = re.sub(r'[^-a-z0-9]', '-', name.lower())
    logging.info("Converted \"{}\" to \"{}\" for"
                 " TPR/CRD name".format(name, name_con))
    if not re.fullmatch('[a-z0-9]([-a-z0-9]*[a-z0-9])?', name_con):
        logging.error("Cant create valid TPR/CRD name using "
                      "\"{}\" - must match regex "
                      "[a-z0-9]([-a-z0-9]*[a-z0-9])?".format(name_con))
        exit(1)
    return name_con


# Utility function to parse K8s version strings into basic semver format.
# NOTE: Based on regexp used in Kubernetes source code here:
# https://github.com/kubernetes/kubernetes/blob/v1.11.3/pkg/util/version/version.go#L37
# NOTE: Extra parts such as pre-release and build metadata are ignored.
def parse_version(version_str):
    version_regex = r"^\s*v?([0-9]+(?:\.[0-9]+)*).*"
    matches = re.search(version_regex, version_str, re.UNICODE)
    if matches:
        return parse(matches.group(1))
    else:
        raise ValueError("Could not parse %s as version string" % version_str)


def generate_key(size):
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=size,
        backend=default_backend()
    )


def generate_cert(service, namespace, private_key):
    name = x509.Name([
        x509.NameAttribute(x509.oid.NameOID.COMMON_NAME,
                           "{0}.{1}.svc".format(service, namespace))
    ])

    subj_alternative_names = x509.SubjectAlternativeName([
        x509.DNSName("{0}".format(service, namespace)),
        x509.DNSName("{0}.{1}".format(service, namespace)),
        x509.DNSName("{0}.{1}.svc".format(service, namespace)),
    ])

    constraints = x509.BasicConstraints(ca=True, path_length=None)

    now = datetime.now()

    cert_builder = x509.CertificateBuilder()
    cert_builder = (cert_builder.subject_name(name)
                                .issuer_name(name)
                                .add_extension(subj_alternative_names, False)
                                .add_extension(constraints, False)
                                .not_valid_before(now)
                                .not_valid_after(now + timedelta(days=36500))
                                .public_key(private_key.public_key())
                                .serial_number(x509.random_serial_number()))

    cert = cert_builder.sign(private_key, hashes.SHA256(), default_backend())
    return cert


def generate_secrets(service, namespace):
    private_key = generate_key(2048)
    cert = generate_cert(service, namespace, private_key)

    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        encryption_algorithm=serialization.NoEncryption(),
        format=serialization.PrivateFormat.TraditionalOpenSSL,
    )

    return b64encode(cert_pem).decode(), b64encode(private_key_pem).decode()


def convert_array2bitmask(array):
    bitmask = 0
    for val in array:
        bitmask = bitmask | (1 << val)
    return str(hex(bitmask))[2:].upper()
