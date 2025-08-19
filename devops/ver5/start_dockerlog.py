#!/usr/env/bin/ python3

import datetime
import logging.handlers
import os
import threading
import time

import docker

LOG_DIR = '/logs'
LOG_SIZE = int(os.environ.get('DSA_LOGGER_LOG_SIZE', 10 * 1024 ** 2))
# This excludes the "0th" log
LOG_COUNT = int(os.environ.get('DSA_LOGGER_LOG_COUNT', 5))
ATTACH_INTERVAL = float(os.environ.get('DSA_LOGGER_REATTACH_INTERVAL', 60))


PrintLock = threading.Lock()


def get_container_network_name(client):
    """
    Get the current network name.

    :param client: the docker client.
    :returns: the network name
    """
    container_id = os.getenv('HOSTNAME')
    container = client.containers.get(container_id)
    network_names = list(container.attrs['NetworkSettings']['Networks'].keys())
    return network_names[0]


def get_compose_services(client, network):
    """
    Get a list of services started in a specific docker network.  Exclude the
    service named logging.

    :param client: the docker client.
    :param network: the name of the network
    :returns: a dictionary with the service name as keys and docker containers
        as values.
    """
    containers = client.containers.list()
    service_map = {}
    for c in containers:
        if network not in c.attrs['NetworkSettings']['Networks'].keys():
            continue
        if c.status != 'running':
            continue
        labels = c.attrs.get('Config', {}).get('Labels', {})
        if 'com.docker.compose.service' in labels:
            svc = labels['com.docker.compose.service']
            if svc != 'logging':
                service_map[svc] = c
    return service_map


def start_logging(service, container, procs):
    """
    Log a specific docker container to a rotated log file.

    :param service: name of the service for logging purposes.  Files will be
        <service>.log, unless the service name is "girder", in which case they
        will be info.log.
    :param container: docker container to log.
    """
    with PrintLock:
        print(f'Starting logs for {service}')
    log_file = os.path.join(LOG_DIR, f'{service if service != "girder" else "info"}.log')
    logger = logging.getLogger(service)
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=LOG_SIZE, backupCount=LOG_COUNT)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info('=' * 78)
    logger.info(f'Starting {service} container log: {datetime.datetime.now().isoformat()}')
    logger.info('=' * 78)
    try:
        for line in container.logs(
                stream=True, follow=True, since=time.time() - ATTACH_INTERVAL * 2):
            logger.info(line.decode().rstrip())
    except Exception:
        pass
    with PrintLock:
        print(f'Stopped logging {service}')
    try:
        procs.pop(service)
    except Exception:
        with PrintLock:
            print(f'Cannot remove {service} from logging list')
    logger.removeHandler(handler)


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
                    target=start_logging, args=(svc, c, procs), daemon=True).start()
        time.sleep(ATTACH_INTERVAL)


if __name__ == '__main__':
    main()
