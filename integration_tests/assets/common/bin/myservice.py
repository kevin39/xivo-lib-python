#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import requests
import sys
import signal
import logging
import os

from flask import Flask, jsonify

from xivo.consul_helpers import ServiceCatalogRegistration

UUID = 'foobar'

app = Flask('myservice')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


@app.route('/0.1/infos')
def infos():
    return jsonify({'uuid': UUID})


def self_check():
    try:
        return requests.get('http://localhost:6262/0.1/infos').status_code == 200
    except Exception:
        pass
    return False


def handler(signum, frame):
    logger.debug('SIGTERM %s', signum)
    sys.exit(0)


def main():
    advertise_address = os.getenv('ADVERTISE_ADDR', 'auto')
    enabled = os.getenv('DISABLED', '0') == '0'
    logger.debug('advertise addr: %s', advertise_address)
    logger.debug('enabled: %s', enabled)

    config = {'consul': {'host': 'consul',
                         'port': 8500,
                         'token': 'the_one_ring'},
              'service_discovery': {'advertise_address': advertise_address,
                                    'advertise_address_interface': 'eth0',
                                    'advertise_port': 6262,
                                    'ttl_interval': 30,
                                    'refresh_interval': 27,
                                    'retry_interval': 2},
              'bus': {'username': 'guest',
                      'password': 'guest',
                      'host': 'rabbitmq',
                      'port': 5672,
                      'exchange_name': 'xivo',
                      'exchange_type': 'topic'},
              'uuid': UUID}

    if not enabled:
        config['service_discovery']['enabled'] = False

    signal.signal(signal.SIGTERM, handler)
    with ServiceCatalogRegistration('myservice',
                                    config['uuid'],
                                    config['consul'],
                                    config['service_discovery'],
                                    config['bus'],
                                    self_check):
        app.run(host="0.0.0.0", port=6262)


if __name__ == '__main__':
    main()
