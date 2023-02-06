#!/usr/bin/env python3

import argparse
import configparser
import logging
import os
import sys
import subprocess
import yaml

logger = logging.getLogger(__name__)
# See http://docs.python.org/3.3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())

def merge_yaml_opts(opts, parser):
    """
    Parse a yaml file of provisioning options.  Modify the options used for
    provisioning.

    :param opts: the options parsed from the command line.
    :param parser: command line parser used to check if the options are the
        default values.
    :return opts: the modified options.
    """
    yamlfile = os.environ.get('DSA_PROVISION_WORKER_YAML') if getattr(
        opts, 'yaml', None) is None else opts.yaml
    if yamlfile:
        logger.debug('Parse yaml file: %r', yamlfile)
    if not yamlfile or not os.path.exists(yamlfile):
        return opts
    defaults = parser.parse_args(args=[])
    yamlopts = yaml.safe_load(open(yamlfile).read())
    for key, value in yamlopts.items():
        key = key.replace('_', '-')
        if getattr(opts, key, None) is None or getattr(
                opts, key, None) == getattr(defaults, key, None):
            setattr(opts, key, value)
    logger.debug('Arguments after adding yaml: %r', opts)
    return opts

def preprovision(opts):
    """
    Preprovision the instance.  This includes installing python modules with
    pip and rebuilding the girder client if desired.

    :param opts: the argparse options.
    """
    if getattr(opts, 'pip', None) and len(opts.pip):
        print('PIP OPTIONS:')
        print(opts.pip)
        for entry in opts.pip:
            cmd = 'pip install %s' % entry
            logger.info('Installing: %s', cmd)
            subprocess.check_call(cmd, shell=True)

def get_ffmpeg():
    cmd = 'wget -O ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && mkdir /tmp/ffextracted && tar -xvf ffmpeg.tar.xz -C /tmp/ffextracted --strip-components 1 && cp /tmp/ffextracted/ffmpeg /opt/venv/bin && cp /tmp/ffextracted/ffprobe /opt/venv/bin'
    subprocess.check_call(cmd, shell=True)

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
        '--pip', action='append', help='A list of modules to pip install.  If '
        'any are specified that include girder client plugins, also specify '
        '--rebuild-client.  Each specified value is passed to pip install '
        'directly, so additional options are needed, these can be added (such '
        'as --find-links).  The actual values need to be escaped '
        'appropriately for a bash shell.')
    parser.add_argument(
        '--verbose', '-v', action='count', default=0, help='Increase verbosity')
    opts = parser.parse_args(args=sys.argv[1:])
    opts = merge_yaml_opts(opts, parser)
    logger.addHandler(logging.StreamHandler(sys.stderr))
    logger.setLevel(max(1, logging.WARNING - 10 * opts.verbose))
    logger.debug('Parsed arguments: %r', opts)
    preprovision(opts)
    get_ffmpeg()
    opts = merge_environ_opts(opts)
    adjust_worker_cfg(opts)
