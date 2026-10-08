#!/usr/bin/env python3

import argparse
import configparser
import logging
import os
import subprocess
import sys
import tempfile
import time

import yaml

logger = logging.getLogger(__name__)
# See http://docs.python.org/3.3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())


def get_collection_folder(adminUser, collName, folderName):
    from girder.models.collection import Collection
    from girder.models.folder import Folder

    if Collection().findOne({'lowerName': collName.lower()}) is None:
        logger.info('Create collection %s', collName)
        Collection().createCollection(collName, adminUser)
    collection = Collection().findOne({'lowerName': collName.lower()})
    if Folder().findOne({
            'parentId': collection['_id'], 'lowerName': folderName.lower()}) is None:
        logger.info('Create folder %s in %s', folderName, collName)
        Folder().createFolder(collection, folderName, parentType='collection',
                              public=True, creator=adminUser)
    folder = Folder().findOne({'parentId': collection['_id'], 'lowerName': folderName.lower()})
    return folder


def get_sample_data(adminUser, collName='Sample Images', folderName='Images'):
    """
    As needed, download sample data.

    :param adminUser: a user to create and modify collections and folders.
    :param collName: the collection name where the data will be added.
    :param folderName: the folder name where the data will be added.
    :returns: the folder where the sample data is located.
    """
    try:
        import girder_client
        import requests
        import urllib3
    except ImportError:
        logger.error('girder_client is unavailable.  Cannot get sample data.')
        return
    from girder.models.item import Item
    from girder.models.upload import Upload
    from girder_large_image.models.image_item import ImageItem

    folder = get_collection_folder(adminUser, collName, folderName)
    remote = girder_client.GirderClient(apiUrl='https://data.kitware.com/api/v1')
    session = requests.Session()
    retries = urllib3.util.retry.Retry(
        total=10, backoff_factor=0.1, status_forcelist=[104, 500, 502, 503, 504])
    session.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))
    remote._session = session

    remoteFolder = remote.resourceLookup('/collection/HistomicsTK/Deployment test images')
    sampleItems = []
    for remoteItem in remote.listItem(remoteFolder['_id']):
        item = Item().findOne({'folderId': folder['_id'], 'name': remoteItem['name']})
        if item and len(list(Item().childFiles(item, limit=1))):
            sampleItems.append(item)
            continue
        if not item:
            item = Item().createItem(remoteItem['name'], creator=adminUser, folder=folder)
        for remoteFile in remote.listFile(remoteItem['_id']):
            with tempfile.NamedTemporaryFile() as tf:
                fileName = tf.name
                tf.close()
                logger.info('Downloading %s', remoteFile['name'])
                remote.downloadFile(remoteFile['_id'], fileName)
                Upload().uploadFromFile(
                    open(fileName, 'rb'), os.path.getsize(fileName),
                    name=remoteItem['name'], parentType='item',
                    parent=item, user=adminUser)
        sampleItems.append(item)
    for item in sampleItems:
        if 'largeImage' not in item:
            logger.info('Making large_item %s', item['name'])
            try:
                ImageItem().createImageItem(item, createJob=False)
            except Exception:
                pass
            logger.info('done')
    return folder


def value_from_resource(value, adminUser):
    """
    If a value is a string that startwith 'resource:', it is a path to an
    existing resource.  Fetch it an return the string of the _id.

    :param value: a value
    :returns: the original value it is not a resource, or the string id of the
        resource.
    """
    import girder.utility.path as path_util
    from girder.models.assetstore import Assetstore

    starts = {'resource:': 'doc', 'resourceid:': 'id', 'resourceobjid:': 'obj'}
    if isinstance(value, dict):
        value = {k: value_from_resource(v, adminUser) for k, v in value.items()}
    for start, stype in starts.items():
        if str(value).startswith(start):
            resPath = value.split(':', 1)[1]
            if resPath == 'admin':
                resource = adminUser
            elif resPath.startswith('assetstore/'):
                resource = Assetstore().findOne({'name': value.split('/', 1)[1]})
            else:
                resource = path_util.lookUpPath(resPath, force=True)['document']
            logger.info(f'Finding {start} reference for {resPath} as '
                        f'{resource["_id"] if resource else resource}')
            if stype == 'doc':
                value = resource
            elif stype == 'id':
                value = str(resource['_id'])
            else:
                value = resource['_id']
            break
    return value


def provision_resources(resources, adminUser):
    """
    Given a dictionary of resources, add them to the system.  The resource is
    only added if a resource of that name with the same parent object does not
    exist.

    :param resources: a list of resources to add.
    :param adminUser: the admin user to use for provisioning.
    """
    from girder.utility.model_importer import ModelImporter

    for entry in resources:
        entry = {k: value_from_resource(v, adminUser) for k, v in entry.items()}
        modelName = entry.pop('model')
        metadata = entry.pop('metadata', None)
        metadata_update = entry.pop('metadata_update', True)
        metadata_key = entry.pop('metadata_key', 'meta')
        attrs = entry.pop('attrs', None)
        attrs_update = entry.pop('attrs_update', True)
        model = ModelImporter.model(modelName)
        key = 'name' if model != 'user' else 'login'
        query = {}
        if key in entry:
            query[key] = entry[key]
        owners = {'folder': 'parent', 'item': 'folder', 'file': 'item'}
        ownerKey = owners.get(modelName)
        if ownerKey and ownerKey in entry and isinstance(
                entry[ownerKey], dict) and '_id' in entry[ownerKey]:
            query[ownerKey + 'Id'] = entry[ownerKey]['_id']
        if query and model.findOne(query):
            result = model.findOne(query)
            logger.debug('Has %s (%r)', modelName, entry)
        else:
            createFunc = getattr(model, 'create%s' % modelName.capitalize())
            logger.info('Creating %s (%r)', modelName, entry)
            result = createFunc(**entry)
            attrs_update = True
        if isinstance(metadata, dict) and hasattr(model, 'setMetadata'):
            if metadata_key not in metadata or metadata_update:
                if metadata_key not in result:
                    result[metadata_key] = {}
                result[metadata_key].update(metadata.items())
                for key in metadata:
                    if metadata[key] is None:
                        del result[metadata_key][key]
                model.validateKeys(result[metadata_key])
                result = model.save(result)
        if attrs and attrs_update:
            result.update(attrs)
            result = model.save(result)


def get_slicer_images(imageList, adminUser, alwaysPull=False):
    """
    Load a list of cli docker images into the system.

    :param imageList: a list of docker images.
    :param adminUser: an admin user for permissions.
    :param alwaysPull: true to ask to always pull the latest image.
    """
    import threading

    from girder import logger
    from girder.models.setting import Setting
    from girder_jobs.constants import JobStatus
    from girder_jobs.models.job import Job
    from slicer_cli_web.config import PluginSettings
    from slicer_cli_web.docker_resource import DockerResource
    from slicer_cli_web.image_job import jobPullAndLoad

    imageList = [entry for entry in imageList if entry and len(entry)]
    if not len(imageList):
        return
    logger.info('Pulling and installing slicer_cli images: %r', imageList)
    job = Job().createLocalJob(
        module='slicer_cli_web.image_job',
        function='jobPullAndLoad',
        kwargs={
            'nameList': imageList,
            'folder': Setting().get(PluginSettings.SLICER_CLI_WEB_TASK_FOLDER),
            'pull': 'true' if alwaysPull else 'asneeded',
        },
        title='Pulling and caching docker images',
        type=DockerResource.jobType,
        user=adminUser,
        public=True,
        asynchronous=True
    )
    job = Job().save(job)
    t = threading.Thread(target=jobPullAndLoad, args=(job, ))
    t.start()
    logpos = 0
    logger.info('Result:\n')
    while job['status'] not in {JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED}:
        time.sleep(0.1)
        job = Job().load(id=job['_id'], user=adminUser, includeLog=True)
        if 'log' in job:
            while logpos < len(job['log']):
                if 'Pulling' not in job['log'][logpos] or '%' not in job['log'][logpos]:
                    logger.info(job['log'][logpos].rstrip())
                logpos += 1
    t.join()
    if 'log' not in job:
        logger.warning('Job record: %r', job)
    if job['status'] != JobStatus.SUCCESS:
        raise Exception('Failed to pull and load images')


def pip_install(packages):
    """
    Pip install a list of packages via the shell pip install command.  This
    first tries installing all of the packages in a single command; if it
    fails, they are tried individually to betetr show where the failure occurs.

    :param packages: a list of strings to add to the end of the pip install
        command.
    """
    if not packages or not len(packages):
        return
    cmd = 'pip install -q ' + ' '.join(packages)
    logger.info('Installing: %s', cmd)
    try:
        subprocess.check_call(cmd, shell=True)
    except Exception:
        logger.error(f'Failed to run {cmd}; trying pip install individually.')
        for entry in packages:
            cmd = 'pip install %s' % entry
            logger.info('Installing: %s', cmd)
            try:
                subprocess.check_call(cmd, shell=True)
            except Exception:
                logger.error(f'Failed to run {cmd}')
                raise


def preprovision(opts):
    """
    Preprovision the instance.  This includes installing python modules with
    pip and rebuilding the girder client if desired.

    :param opts: the argparse options.
    """
    pip_install(getattr(opts, 'pip', None))
    if getattr(opts, 'shell', None) and len(opts.shell):
        for entry in opts.shell:
            cmd = entry
            logger.info('Running: %s', cmd)
            try:
                subprocess.check_call(cmd, shell=True)
            except Exception:
                logger.error(f'Failed to run {cmd}')
                raise
    if getattr(opts, 'rebuild-client', None):
        cmd = 'girder build'
        if str(getattr(opts, 'rebuild-client', None)).lower().startswith('dev'):
            cmd += ' --dev'
        logger.info('Rebuilding girder client: %s', cmd)
        cmd = ('NPM_CONFIG_FUND=false NPM_CONFIG_AUDIT=false '
               'NPM_CONFIG_AUDIT_LEVEL=high NPM_CONFIG_LOGLEVEL=error '
               'NPM_CONFIG_PROGRESS=false NPM_CONFIG_PREFER_OFFLINE=true ' + cmd)
        try:
            if not getattr(opts, 'no_wait', False):
                subprocess.check_call(cmd, shell=True)
            else:
                proc = subprocess.Popen(cmd + ' ; touch /tmp/girder_build_done', shell=True)
                logger.info('Rebuilding in background via pid %r', proc.pid)
                open('/tmp/girder_build.pid', 'w').write(str(proc.pid))
        except Exception:
            logger.error(f'Failed to run {cmd}')
            raise


def clean_delete_locks():
    from girder.constants import AssetstoreType
    from girder.models.assetstore import Assetstore

    for assetstore in Assetstore().find():
        if assetstore['type'] != AssetstoreType.FILESYSTEM:
            continue
        rootpath = assetstore['root']
        cmd = ['find', rootpath, '-name', '*.deleteLock', '-delete']
        logger.info(f'Removing old delete locks: {cmd}')
        try:
            subprocess.check_call(cmd, shell=False)
        except Exception:
            logger.info(f'Failed trying to remove old delete locks: {cmd}')


def provision(opts):  # noqa
    """
    Provision the instance.

    :param opts: the argparse options.
    """
    from girder.models.assetstore import Assetstore
    from girder.models.setting import Setting
    from girder.models.user import User

    # If there is are no admin users, create an admin user
    if User().findOne({'admin': True}) is None:
        adminParams = dict({
            'login': 'admin',
            'password': 'password',
            'firstName': 'Admin',
            'lastName': 'Admin',
            'email': 'admin@nowhere.nil',
            'public': True,
        }, **(opts.admin if opts.admin else {}))
        User().createUser(admin=True, **adminParams)
    adminUser = User().findOne({'admin': True})

    # Make sure we have an assetstore
    assetstoreParams = opts.assetstore or {'name': 'Assetstore', 'root': '/assetstore'}
    if not isinstance(assetstoreParams, list):
        assetstoreParams = [assetstoreParams]
    if Assetstore().findOne() is None:
        for params in assetstoreParams:
            method = params.pop('method', 'createFilesystemAssetstore')
            getattr(Assetstore(), method)(**params)

    # Clean up old deleteLocks
    if getattr(opts, 'clean-delete-locks', None):
        clean_delete_locks()

    # Make sure we have a demo collection and download some demo files
    if getattr(opts, 'samples', None):
        get_sample_data(
            adminUser,
            getattr(opts, 'sample-collection', 'Samples'),
            getattr(opts, 'sample-folder', 'Images'))
    if opts.resources:
        provision_resources(opts.resources, adminUser)
    settings = dict({}, **(opts.settings or {}))
    force = getattr(opts, 'force', None) or []
    for key, value in settings.items():
        if (value != '__SKIP__' and (
                force is True or key in force or
                Setting().get(key) is None or
                Setting().get(key) == Setting().getDefault(key))):
            value = value_from_resource(value, adminUser)
            logger.info('Setting %s to %r', key, value)
            Setting().set(key, value)
    images = []
    if getattr(opts, 'slicer-cli-image-pull', None):
        images = list(dict.fromkeys(getattr(opts, 'slicer-cli-image-pull', None)))
        try:
            get_slicer_images(getattr(opts, 'slicer-cli-image-pull', None),
                              adminUser, alwaysPull=True)
        except Exception:
            logger.info('Cannot fetch slicer-cli-images.')
    if getattr(opts, 'slicer-cli-image', None):
        images = [image for image in dict.fromkeys(getattr(opts, 'slicer-cli-image', None))
                  if image not in images]
        try:
            get_slicer_images(images, adminUser)
        except Exception:
            logger.info('Cannot fetch slicer-cli-images.')


def preprovision_worker(opts):
    """
    Preprovision the worker.
    """
    settings = dict({}, **(opts.worker or {}))
    pip_install(settings.get('pip'))
    if settings.get('shell') and len(settings['shell']):
        for entry in settings['shell']:
            cmd = entry
            logger.info('Running: %s', cmd)
            try:
                subprocess.check_call(cmd, shell=True)
            except Exception:
                logger.error(f'Failed to run {cmd}')
                raise


def provision_worker(opts):
    """
    Provision the worker.  There are a few top-level settings, but others
    should be in the worker sub-field.
    """
    settings = dict({}, **(opts.worker or {}))
    for key in dir(opts):
        if key.startswith('worker-'):
            mainkey = key.split('worker-', 1)[1]
            if settings.get(mainkey) is None:
                settings[mainkey] = getattr(opts, key)
    if not settings.get('rabbitmq-host'):
        return
    conf = configparser.ConfigParser()
    conf.read([settings['config']])
    conf.set('celery', 'broker', 'amqp://%s:%s@%s/' % (
        settings['rabbitmq-user'], settings['rabbitmq-pass'], settings['host']))
    conf.set('celery', 'backend', 'rpc://%s:%s@%s/' % (
        settings['rabbitmq-user'], settings['rabbitmq-pass'], settings['host']))
    with open(settings['config'], 'w') as fptr:
        conf.write(fptr)


def merge_environ_opts(opts):
    """
    Merge environment options, overriding other settings.

    :param opts: the options parsed from the command line.
    :return opts: the modified options.
    """
    keyDict = {
        'RABBITMQ_USER': 'worker_rabbitmq_user',
        'RABBITMQ_PASS': 'worker_rabbitmq_pass',
        'DSA_RABBITMQ_HOST': 'worker_rabbitmq_host',
    }
    for key, value in os.environ.items():
        if not value or not value.strip():
            continue
        if key == 'DSA_WORKER_API_URL':
            key = 'worker.api_url'
        elif key.startswith('DSA_SETTING_'):
            key = key.split('DSA_SETTING_', 1)[1]
        elif key in keyDict:
            key = keyDict[key]
        else:
            continue
        opts.settings[key] = value
        if not opts.force:
            opts.force = {key}
        elif opts.force is not True:
            opts.force = set(opts.force)
            opts.force.add(key)
    return opts


def merge_yaml_opts(opts, parser):
    """
    Parse a yaml file of provisioning options.  Modify the options used for
    provisioning.

    :param opts: the options parsed from the command line.
    :param parser: command line parser used to check if the options are the
        default values.
    :return opts: the modified options.
    """
    yamlfile = os.environ.get('DSA_PROVISION_YAML') if getattr(
        opts, 'yaml', None) is None else opts.yaml
    if yamlfile:
        logger.debug('Parse yaml file: %r', yamlfile)
    if not yamlfile or not os.path.exists(yamlfile):
        return opts
    defaults = parser.parse_args(args=[])
    if getattr(opts, 'use-defaults', None) is not False:
        defaults = merge_default_opts(defaults)
    yamlopts = yaml.safe_load(open(yamlfile).read())
    for key, value in yamlopts.items():
        key = key.replace('_', '-')
        if getattr(opts, key, None) is None or getattr(
                opts, key, None) == getattr(defaults, key, None):
            if key == 'settings' and getattr(opts, key, None) and isinstance(value, dict):
                getattr(opts, key).update(value)
            else:
                setattr(opts, key, value)
    logger.debug('Arguments after adding yaml: %r', opts)
    return opts


def merge_default_opts(opts):
    """
    Add the defaults to the options.

    :param opts: the options parsed from the command line.
    :return opts: the modified options.
    """
    settings = dict({}, **(opts.settings or {}))
    settings.update({
        'worker.broker': 'amqp://guest:guest@rabbitmq',
        'worker.backend': 'rpc://guest:guest@rabbitmq',
        'worker.api_url': 'http://girder:8080/api/v1',
        'worker.direct_path': True,
        'core.brand_name': 'Digital Slide Archive',
        # 'core.http_only_cookies': True,
        'histomicsui.webroot_path': 'histomics',
        'histomicsui.alternate_webroot_path': 'histomicstk',
        'histomicsui.delete_annotations_after_ingest': True,
        'homepage.markdown': """# Digital Slide Archive
---
## Bioinformatics Platform

Welcome to the **Digital Slide Archive**.

Developers who want to use the Girder REST API should check out the
[interactive web API docs](api/v1).

The [HistomicsUI](histomics) application is enabled.""",
        'slicer_cli_web.task_folder': 'resourceid:collection/Tasks/Slicer CLI Web Tasks',
    })
    opts.settings = settings
    if getattr(opts, 'slicer-cli-image-pull', None) is None:
        setattr(opts, 'slicer-cli-image-pull', ['dsarchive/histomicstk:latest'])
    if getattr(opts, 'assetstore', None) is None:
        opts.assetstore = {
            'name': 'Assetstore',
            'root': '/assetstore',
            'method': 'createFilesystemAssetstore',
        }
    if getattr(opts, 'admin', None) is None:
        opts.admin = {
            'login': 'admin',
            'password': 'password',
            'firstName': 'Admin',
            'lastName': 'Admin',
            'email': 'admin@nowhere.nil',
            'public': True,
        }
    if getattr(opts, 'clean-delete-locks', None) is None:
        setattr(opts, 'clean-delete-locks', True)
    resources = opts.resources or []
    resources.extend([{
        'model': 'collection',
        'name': 'Tasks',
        'creator': 'resource:admin',
        'public': True,
    }, {
        'model': 'folder',
        'parent': 'resource:collection/Tasks',
        'parentType': 'collection',
        'name': 'Slicer CLI Web Tasks',
        'creator': 'resource:admin',
        'public': True,
    }])
    opts.resources = resources
    return opts


class YamlAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        """Parse a yaml entry"""
        if nargs is not None:
            raise ValueError('nargs not allowed')
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, yaml.safe_load(values))


if __name__ == '__main__':  # noqa
    parser = argparse.ArgumentParser(description='Provision a Digital Slide Archive instance')
    parser.add_argument(
        '--force', action='store_true',
        help='Reset all settings.  This does not change the admin user or the '
        'default assetstore if those already exist.  Otherwise, settings are '
        'only added or modified if they do not exist or are the default '
        'value.')
    parser.add_argument(
        '--samples', '--data', '--sample-data',
        action='store_true', help='Download sample data')
    parser.add_argument(
        '--clean-delete-locks', action='store_true',
        help='Remove assetstore delete locks on start')
    parser.add_argument(
        '--no-clean-delete-locks', action='store_false',
        dest='clean-delete-locks',
        help='Do not remove assetstore delete locks on start')
    parser.add_argument(
        '--sample-collection', dest='sample-collection', default='Samples',
        help='Sample data collection name')
    parser.add_argument(
        '--sample-folder', dest='sample-folder', default='Images',
        help='Sample data folder name')
    parser.add_argument(
        '--admin', action=YamlAction,
        help='A yaml dictionary of parameters used to create a default admin '
        'user.  If any of login, password, firstName, lastName, email, or '
        'public are not specified, some default values are used.  If any '
        'admin user already exists, no modifications are made.')
    parser.add_argument(
        '--assetstore', action=YamlAction,
        help='A yaml dictionary (or list of dictionaries) of parameters used '
        'to create a default assetstore.  This can include "method" which '
        'includes the creation method, such as "createFilesystemAssetstore" '
        'or "createS3Assetstore".  Otherwise, this is a list of parameters '
        'passed to the creation method.  For filesystem assetstores, these '
        'parameters are name, root, and perms.  For S3 assetstores, these are '
        'name, bucket, accessKeyId, secret, prefix, service, readOnly, '
        'region, inferCredentials, and serverSideEncryption.  If unspecified, '
        'a filesystem assetstore is created.')
    parser.add_argument(
        '--settings', action=YamlAction,
        help='A yaml dictionary of settings to change in the Girder '
        'database.  This is merged with the default settings dictionary.  '
        'Settings are only changed if they are their default values, the '
        'force option is used, or they are specified by an environment '
        'variable.  If a setting has a value of "__SKIP__", it will not be '
        'changed (this can prevent setting a default setting '
        'option to any value).')
    parser.add_argument(
        '--resources', action=YamlAction,
        help='A yaml list of resources to add by name to the Girder '
        'database.  Each entry is a dictionary including "model" with the '
        'resource model and a dictionary of values to pass to the '
        'appropriate create(resource) function.  A value of '
        '"resource:<path>" is converted to the resource document with that '
        'resource path.  "resource:admin" uses the default admin, '
        '"resourceid:<path>" is the string id for the resource path.')
    parser.add_argument(
        '--yaml',
        help='Specify parameters for this script in a yaml file.  If no value '
        'is specified, this defaults to the environment variable of '
        'DSA_PROVISION_YAML.  No error is thrown if the file does not exist. '
        'The yaml file is a dictionary of keys as would be passed to the '
        'command line.')
    parser.add_argument(
        '--no-mongo-compat', action='store_false', dest='mongo-compat',
        default=True, help='Do not automatically set the mongo feature '
        'compatibility version to the current server version.')
    parser.add_argument(
        '--no-defaults', action='store_false', dest='use-defaults',
        default=None, help='Do not use default settings; start with a minimal '
        'number of parameters.')
    parser.add_argument(
        '--pip', action='append', help='A list of modules to pip install.  If '
        'any are specified that include girder client plugins, also specify '
        '--rebuild-client.  Each specified value is passed to pip install '
        'directly, so additional options are needed, these can be added (such '
        'as --find-links).  The actual values need to be escaped '
        'appropriately for a bash shell.')
    parser.add_argument(
        '--rebuild-client', dest='rebuild-client', action='store_true',
        default=False, help='Rebuild the girder client.')
    parser.add_argument(
        '--slicer-cli-image', dest='slicer-cli-image', action='append',
        help='Install slicer_cli images, only pulling if not present.')
    parser.add_argument(
        '--slicer-cli-image-pull', dest='slicer-cli-image-pull', action='append',
        help='Install slicer_cli images, always pulling the latest.')

    parser.add_argument(
        '--rabbitmq-user', default='guest', dest='worker-rabbitmq-user',
        help='Worker: RabbitMQ user name.')
    parser.add_argument(
        '--rabbitmq-pass', default='guest', dest='worker-rabbitmq-pass',
        help='Worker: RabbitMQ password.')
    parser.add_argument(
        '--rabbitmq-host', dest='worker-rabbitmq-host',
        help='Worker: RabbitMQ host.')
    parser.add_argument(
        '--config', dest='worker-config',
        default='/opt/girder_worker/girder_worker/worker.local.cfg',
        help='Worker: Path to the worker config file.')
    parser.add_argument(
        '--worker', action=YamlAction,
        help='A yaml dictionary of worker settings.')
    parser.add_argument(
        '--worker-main', dest='portion', action='store_const',
        const='worker-main',
        help='Provision a worker, not the main process.')
    parser.add_argument(
        '--worker-pre', dest='portion', action='store_const',
        const='worker-pre',
        help='Pre-provision a worker, not the main process.')
    parser.add_argument(
        '--pre', dest='portion', action='store_const', const='pre',
        help='Only do preprovisioning (install optional python modules and '
        'optionally build the girder client).')
    parser.add_argument(
        '--main', dest='portion', action='store_const', const='main',
        help='Only do main provisioning.')
    parser.add_argument(
        '--no-wait', action='store_true',
        help='If a girder build is performed during preprovisioning, do not '
        'wait for it to complete.')
    parser.add_argument(
        '--verbose', '-v', action='count', default=0, help='Increase verbosity')
    parser.add_argument(
        '--dry-run', '-n', dest='dry-run', action='store_true',
        help='Report merged options but do not actually apply them')
    opts = parser.parse_args(args=sys.argv[1:])
    logger.addHandler(logging.StreamHandler(sys.stderr))
    logger.setLevel(max(1, logging.WARNING - 10 * opts.verbose))
    try:
        logger.info('Provision file date: %s; size: %d',
                    time.ctime(os.path.getmtime(__file__)),
                    os.path.getsize(__file__))
    except Exception:
        pass
    logger.debug('Parsed arguments: %r', opts)
    if getattr(opts, 'use-defaults', None) is not False:
        opts = merge_default_opts(opts)
    opts = merge_yaml_opts(opts, parser)
    opts = merge_environ_opts(opts)
    logger.debug('Merged arguments: %r', opts)
    if getattr(opts, 'dry-run'):
        print(yaml.dump({k: v for k, v in vars(opts).items() if v is not None}))
        sys.exit(0)
    # Worker provisioning
    if getattr(opts, 'portion', None) == 'worker-pre':
        preprovision_worker(opts)
        sys.exit(0)
    if getattr(opts, 'portion', None) == 'worker-main':
        provision_worker(opts)
        sys.exit(0)
    if getattr(opts, 'portion', None) in {'pre', None}:
        # Run provisioning that has to happen before configuring the server.
        preprovision(opts)
        if getattr(opts, 'portion', None) == 'pre':
            sys.exit(0)
    if getattr(opts, 'portion', None) in {'main', None}:
        # This loads plugins, allowing setting validation.  We want the import
        # to be after the preprovision step.
        from girder import _attachFileLogHandlers
        from girder.utility.server import configureServer

        _attachFileLogHandlers()
        configureServer()
        if getattr(opts, 'mongo-compat', None) is not False:
            from girder.models import getDbConnection

            try:
                db = getDbConnection()
            except Exception:
                logger.warning('Could not connect to mongo.')
            try:
                # In mongo shell, this is functionally
                #   db.adminCommand({setFeatureCompatibilityVersion:
                #     db.version().split('.').slice(0, 2).join('.')})
                db.admin.command({'setFeatureCompatibilityVersion': '.'.join(
                    db.server_info()['version'].split('.')[:2]), 'confirm': True})
            except Exception:
                try:
                    db.admin.command({'setFeatureCompatibilityVersion': '.'.join(
                        db.server_info()['version'].split('.')[:2])})
                except Exception:
                    logger.warning('Could not set mongo feature compatibility version.')
            try:
                # Also attempt to upgrade old version 2 image sources
                db.girder.item.update_many(
                    {'largeImage.sourceName': 'svs'},
                    {'$set': {'largeImage.sourceName': 'openslide'}})
            except Exception:
                logger.warning('Could not update old source names.')
        provision(opts)
