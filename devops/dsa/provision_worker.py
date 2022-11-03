#!/usr/bin/env python3

import argparse
import configparser
import logging
import os
import sys

logger = logging.getLogger(__name__)
# See http://docs.python.org/3.3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())


def adjust_worker_cfg(opts):
    """
    Modify the worker.local.conf file based on the settings.

    :param opts: the options to apply.
    """
    if not opts.rabbitmq_host:
        return
    conf = configparser.ConfigParser()
    conf.read([opts.config])
    conf.set('celery', 'broker', 'amqp://%s:%s@%s/' % (
        opts.rabbitmq_user, opts.rabbitmq_pass, opts.rabbitmq_host))
    conf.set('celery', 'backend', 'rpc://%s:%s@%s/' % (
        opts.rabbitmq_user, opts.rabbitmq_pass, opts.rabbitmq_host))
    with open(opts.config, 'wt') as fptr:
        conf.write(fptr)


def merge_environ_opts(opts):
    """
    Merge environment options, overriding other settings.

    :param opts: the options parsed from the command line.
    :return opts: the modified options.
    """
    for key, value in os.environ.items():
        if not value or not value.strip():
            continue
        if key == 'RABBITMQ_USER':
            opts.rabbitmq_user = value
        elif key == 'RABBITMQ_PASS':
            opts.rabbitmq_pass = value
        elif key == 'DSA_RABBITMQ_HOST':
            opts.rabbitmq_host = value
    return opts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Provision a Digital Slide Archive worker instance')
    parser.add_argument(
        '--rabbitmq-user', default='guest', help='RabbitMQ user name.')
    parser.add_argument(
        '--rabbitmq-pass', default='guest', help='RabbitMQ password.')
    parser.add_argument(
        '--rabbitmq-host', help='RabbitMQ host.')
    parser.add_argument(
        '--config',
        default='/opt/girder_worker/girder_worker/worker.local.cfg',
        help='Path to the worker config file.')
    parser.add_argument(
        '--verbose', '-v', action='count', default=0, help='Increase verbosity')
    opts = parser.parse_args(args=sys.argv[1:])
    logger.addHandler(logging.StreamHandler(sys.stderr))
    logger.setLevel(max(1, logging.WARNING - 10 * opts.verbose))
    logger.debug('Parsed arguments: %r', opts)
    opts = merge_environ_opts(opts)
    adjust_worker_cfg(opts)
