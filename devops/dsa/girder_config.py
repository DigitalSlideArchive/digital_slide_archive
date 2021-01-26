# This ensures that:
#  - Worker settings are correct
#  - there is at least one admin user
#  - there is a default task folder
#  - there is at least one assetstore

from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.user import User
from girder.utility.server import configureServer

# This loads plugins, allowing setting validation
configureServer()

# Ensure worker settings are correct
Setting().set('worker.broker', 'amqp://guest:guest@rabbitmq/')
Setting().set('worker.backend', 'rpc://guest:guest@rabbitmq/')
Setting().set('worker.api_url', 'http://girder:8080/api/v1')

# If there is are no users, create an admin user
if User().findOne() is None:
    User().createUser('admin', 'password', 'Admin', 'Admin', 'admin@nowhere.nil')
adminUser = User().findOne({'admin': True})
# Make sure we have an assetstore
if Assetstore().findOne() is None:
    Assetstore().createFilesystemAssetstore('Assetstore', '/assetstore')
# If we don't have a default task folder, make a task collection and folder
if not Setting().get('slicer_cli_web.task_folder'):
    # Make sure we have a Tasks collection with a Slicer CLI Web Tasks folder
    if Collection().findOne({'name': 'Tasks'}) is None:
        Collection().createCollection('Tasks', adminUser)
    tasksCollection = Collection().findOne({'name': 'Tasks'})
    taskFolderName = 'Slicer CLI Web Tasks'
    if Folder().findOne({'name': taskFolderName, 'parentId': tasksCollection['_id']}) is None:
        Folder().createFolder(
            tasksCollection, taskFolderName, parentType='collection',
            public=True, creator=adminUser)
    taskFolder = Folder().findOne({'name': taskFolderName, 'parentId': tasksCollection['_id']})
    Setting().set('slicer_cli_web.task_folder', str(taskFolder['_id']))
