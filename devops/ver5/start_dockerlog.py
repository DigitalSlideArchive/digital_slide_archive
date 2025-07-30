#!/usr/env/bin/ python3

import datetime
import logging.handlers
import os
import threading
import time

import docker

LOG_DIR = '/logs'
LOG_SIZE = 10 * 1024 ** 2
LOG_COUNT = 6


def get_compose_services(client, network):
    containers = client.containers.list()
    service_map = {}
    for c in containers:
        if network not in c.attrs['NetworkSettings']['Networks'].keys():
            continue
        labels = c.attrs.get('Config', {}).get('Labels', {})
        if 'com.docker.compose.service' in labels:
            svc = labels['com.docker.compose.service']
            if svc != 'logging':
                service_map[svc] = c
    return service_map


def start_logging(service, container):
    print(f'Starting logs for {service}')
    log_file = os.path.join(LOG_DIR, f'{service if service != "girder" else "info"}.log')
    logger = logging.getLogger(service)
    logger.addHandler(logging.handlers.RotatingFileHandler(
        log_file, maxBytes=LOG_SIZE, backupCount=LOG_COUNT))
    logger.setLevel(logging.INFO)
    logger.info('=' * 78)
    logger.info(f'Starting {service} container log: {datetime.datetime.now().isoformat()}')
    logger.info('=' * 78)
    try:
        for line in container.logs(stream=True, follow=True):
            logger.info(line.decode().rstrip())
    except Exception as exc:
        print(f'Stopped logging {service}: {exc}')


def get_container_network_name(client):
    container_id = os.getenv('HOSTNAME')
    container = client.containers.get(container_id)
    network_names = list(container.attrs['NetworkSettings']['Networks'].keys())
    return network_names[0]


def main():
    print('Starting log tracker')
    client = docker.from_env(version='auto')
    network = get_container_network_name(client)
    procs = {os.getenv('HOSTNAME'): True}
    while True:
        services = get_compose_services(client, network)
        for svc, c in services.items():
            if svc not in procs:
                procs[svc] = threading.Thread(
                    target=start_logging, args=(svc, c), daemon=True).start()
        time.sleep(5)


if __name__ == '__main__':
    main()
