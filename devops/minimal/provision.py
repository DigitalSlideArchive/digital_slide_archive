import argparse
import os
import sys
import tempfile
import yaml

from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.models.user import User
from girder.utility.server import configureServer

import girder_client

from girder_large_image.models.image_item import ImageItem


def get_collection_folder(adminUser, collName, folderName):
    if Collection().findOne({'lowerName': collName.lower()}) is None:
        Collection().createCollection(collName, adminUser)
    collection = Collection().findOne({'lowerName': collName.lower()})
    if Folder().findOne({
            'parentId': collection['_id'], 'lowerName': folderName.lower()}) is None:
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
                sys.stdout.write('Downloading %s' % remoteFile['name'])
                sys.stdout.flush()
                remote.downloadFile(remoteFile['_id'], fileName)
                sys.stdout.write(' .')
                sys.stdout.flush()
                Upload().uploadFromFile(
                    open(fileName, 'rb'), os.path.getsize(fileName),
                    name=remoteItem['name'], parentType='item',
                    parent=item, user=adminUser)
                sys.stdout.write('.\n')
                sys.stdout.flush()
        sampleItems.append(item)
    for item in sampleItems:
        if 'largeImage' not in item:
            sys.stdout.write('Making large_item %s ' % item['name'])
            sys.stdout.flush()
            try:
                ImageItem().createImageItem(item, createJob=False)
            except Exception:
                pass
            print('done')
    return folder


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
            Setting().set(key, value)


class YamlAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
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
        'default assetstore if those already exist.')
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
    opts = parser.parse_args(args=sys.argv[1:])
    # This loads plugins, allowing setting validation
    configureServer()
    provision(opts)
