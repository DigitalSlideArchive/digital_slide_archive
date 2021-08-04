#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import tempfile

import girder.utility.path as path_util
import girder_client
import yaml
from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.models.user import User
from girder.utility.model_importer import ModelImporter
from girder.utility.server import configureServer
from girder_large_image.models.image_item import ImageItem

logger = logging.getLogger(__name__)
# See http://docs.python.org/3.3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())


def get_collection_folder(adminUser, collName, folderName):
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
    :param folderName: the folder name where the data will bed aded.
    :returns: the folder where the sample data is located.
    """
    folder = get_collection_folder(adminUser, collName, folderName)
    remote = girder_client.GirderClient(apiUrl='https://data.kitware.com/api/v1')
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
    if str(value) == 'resourceid:admin':
        value = str(adminUser['_id'])
    elif str(value).startswith('resourceid:'):
        resource = path_util.lookUpPath(value.split(':', 1)[1], force=True)['document']
        value = str(resource['_id'])
    elif str(value) == 'resource:admin':
        value = adminUser
    elif str(value).startswith('resource:'):
        value = path_util.lookUpPath(value.split(':', 1)[1], force=True)['document']
    return value


def provision_resources(resources, adminUser):
    """
    Given a dictionary of resources, add them to the system.  The resource is
    only added if a resource of that name with the same parent object does not
    exist.

    :param resources: a list of resources to add.
    :param adminUser: the admin user to use for provisioning.
    """
    for entry in resources:
        entry = {k: value_from_resource(v, adminUser) for k, v in entry.items()}
        modelName = entry.pop('model')
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
            continue
        createFunc = getattr(model, 'create%s' % modelName.capitalize())
        logger.info('Creating %s (%r)', modelName, entry)
        createFunc(**entry)


def provision(opts):
    """
    Provision the instance.

    :param opts: the argparse options.
    """
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
    assetstoreCreateMethod = assetstoreParams.pop('method', 'createFilesystemAssetstore')
    if Assetstore().findOne() is None:
        getattr(Assetstore(), assetstoreCreateMethod)(**assetstoreParams)

    # Make sure we have a demo collection and download some demo files
    if getattr(opts, 'samples', None):
        get_sample_data(
            adminUser,
            getattr(opts, 'sample-collection', 'TCGA collection'),
            getattr(opts, 'sample-folder', 'Sample Images'))
    taskFolder = get_collection_folder(adminUser, 'Tasks', 'Slicer CLI Web Tasks')
    if opts.resources:
        provision_resources(opts.resources, adminUser)
    # Show label and macro images, plus tile and internal metadata for all users
    settings = dict({
        'worker.broker': 'amqp://guest:guest@rabbitmq',
        'worker.backend': 'rpc://guest:guest@rabbitmq',
        'worker.api_url': 'http://girder:8080/api/v1',
        'worker.direct_path': True,
        'core.brand_name': 'Digital Slide Archive',
        'histomicsui.webroot_path': 'histomics',
        'histomicsui.alternate_webroot_path': 'histomicstk',
        'homepage.markdown': """# Digital Slide Archive
---
## Bioinformatics Platform

Welcome to the **Digital Slide Archive**.

Developers who want to use the Girder REST API should check out the
[interactive web API docs](api/v1).

The [HistomicsUI](histomics) application is enabled.""",
        'slicer_cli_web.task_folder': str(taskFolder['_id']),
    }, **(opts.settings or {}))
    for key, value in settings.items():
        if (value != '__SKIP__' and (
                getattr(opts, 'force', None) or
                Setting().get(key) is None or
                Setting().get(key) == Setting().getDefault(key))):
            value = value_from_resource(value, adminUser)
            logger.info('Setting %s to %r', key, value)
            Setting().set(key, value)


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
    yamlopts = yaml.safe_load(open(yamlfile).read())
    for key, value in yamlopts.items():
        if getattr(opts, key, None) is None or getattr(
                opts, key, None) == getattr(defaults, key, None):
            setattr(opts, key, value)
    logger.debug('Arguments after adding yaml: %r', opts)
    return opts


class YamlAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        """Parse a yaml entry"""
        if nargs is not None:
            raise ValueError('nargs not allowed')
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, yaml.safe_load(values))


if __name__ == '__main__':
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
        '--sample-collection', default='Sample Images', help='Sample data collection name')
    parser.add_argument(
        '--sample-folder', default='Images', help='Sample data folder name')
    parser.add_argument(
        '--admin', action=YamlAction,
        help='A yaml dictionary of parameters used to create a default admin '
        'user.  If any of login, password, firstName, lastName, email, or '
        'public are not specified, some default values are used.')
    parser.add_argument(
        '--assetstore', action=YamlAction,
        help='A yaml dictionary of parameters used to create a default '
        'assetstore.  This can include "method" which includes the creation '
        'method, such as "createFilesystemAssetstore" or '
        '"createS3Assetstore".  Otherwise, this is a list of parameters '
        'passed to the creation method.  For filesystem assetstores, these '
        'parameters are name, root, and perms.  For S3 assetstores, these are '
        'name, bucket, accessKeyId, secret, prefix, service, readOnly, '
        'region, inferCredentials, and serverSideEncryption.  If unspecified, '
        'a filesystem assetstore is created.')
    parser.add_argument(
        '--settings', action=YamlAction,
        help='A yaml dictionary of settings to change in the Girder '
        'database.  This is merged with the default settings dictionary.  '
        'Settings are only changed if they are their default values or the '
        'force option is used.  If a setting has a value of "__SKIP__", it '
        'will not be changed (this can prevent setting a default setting '
        'option to any value).')
    parser.add_argument(
        '--resources', action=YamlAction,
        help='A yaml list of resources to add by name to the Girder '
        'database.  Each entry is a dictionary including "model" with the '
        'resource model and a dictionary of values to pass to the '
        'appropriate create(resource) function.  A value of '
        '"resource:<path>" is converted to the resource document with that '
        'resource path.  "resource:admin" uses the default admin, '
        '"resourceid:<path" is the string id for the resource path.')
    parser.add_argument(
        '--yaml',
        help='Specify parameters for this script in a yaml file.  If no value '
        'is specified, this defaults to the environment variable of '
        'DSA_PROVISION_YAML.  No error is thrown if the file does not exist. '
        'The yaml file is a dictionary of keys as would be passed to the '
        'command line.')
    parser.add_argument(
        '--verbose', '-v', action='count', default=0, help='Increase verbosity')
    opts = parser.parse_args(args=sys.argv[1:])
    logger.addHandler(logging.StreamHandler(sys.stderr))
    logger.setLevel(max(1, logging.WARNING - 10 * opts.verbose))
    logger.debug('Parsed arguments: %r', opts)
    opts = merge_yaml_opts(opts, parser)
    # This loads plugins, allowing setting validation
    configureServer()
    provision(opts)
