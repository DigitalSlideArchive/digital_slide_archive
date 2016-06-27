#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import json

import girder_client


def printHttpError(err):
    print ('Request Error:\n'
           'status:%s\n'
           'response%s\n'
           'url:%s\n'
           'method:%s' % (err.status, err.responseText, err.url, err.method))


def recurseGetResource(client, parentId, resourceType,
                       parentType='folder'):
    """
    Recurse below the parent(indicated by parentId) and generate a list of all
    resources of type resourceType that existed under the parent.

    :param parentId: Id of the collection or folder to be searched.
    :type parentId: ObjectId
    :param resourceType: Either 'item' or 'folder'. Indicates whether nested
    folder data or item data should be collected.
    :type resourceType: str
    :param parentType: Either 'folder' or 'collection'. Indicates whether
    the parentId is a collection id or a folder id.
    :type parentType: str
    :returns: A list of all folders or items below parentId.
    :rtype: list of dict
    """
    # now get all folders
    resourceList = []
    try:
        folders = client.listFolder(parentId, parentFolderType=parentType)
    except girder_client.HttpError as err:
        printHttpError(err)
        return []
    folderIdList = getField(folders, '_id')

    if resourceType is 'item' and parentType is not 'collection':
        try:
            data = client.listItem(parentId)

            resourceList.extend(data)
        except girder_client.HttpError as err:
            printHttpError(err)
            return []
    elif resourceType is 'folder':
        resourceList.extend(folders)
    elif resourceType is not 'item' and resourceType is not 'folder':
        raise Exception('Invalid resourceType: %s' % resourceType)
    for folderId in folderIdList:
        resourceList.extend(
            recurseGetResource(client, folderId, resourceType))
    return resourceList


def printField(data, strKey):
    for i in range(len(data)):
        print(data[i][strKey])


def getField(data, strKey):
    return [i[strKey] for i in data]


def makeLargeImage(gc, itemId):
    # first check if the file is already a large image
    try:
        itemData = gc.getItem(itemId)
    except girder_client.HttpError as err:
        print('bad item id: %s' % itemId)
        raise

    # if the item is already a large image return
    if 'largeImage' not in itemData:
        gc.post('item/%s/tiles' % itemId)


def hasItems(gc, folder):
    itemList = recurseGetResource(gc, folder, 'item',)
    return len(itemList) != 0


GIRDER_LOCATION = 'http://localhost:8080/api/v1'

COLLECTION_NAME = 'DG TCGA'

NEW_FOLDER_NAME = 'GBM'

IMG_TYPE = '.svs'


def main():
    # login to girder, you will be prompted for credentials
    gc = girder_client.GirderClient(apiUrl=GIRDER_LOCATION)
    gc.authenticate(interactive=True)

    # get the id of the desired collection
    requestUrl = 'resource/lookup?path=collection/%s' % COLLECTION_NAME
    collectionData = gc.getResource(requestUrl)

    collectionId = collectionData['_id']

    # create a folder under this collection or
    # load a preexisting folder that exists with the same name and parent
    newFolderData = gc.load_or_create_folder(NEW_FOLDER_NAME,
                                             collectionId, 'collection')
    newFolderId = newFolderData['_id']

    # get a list of all items within each folder of the collection
    itemList = recurseGetResource(gc, collectionId, 'item', 'collection')

    print('Listing all %s items in the collection %s' % (IMG_TYPE,
                                                         COLLECTION_NAME))
    # create a list to store id of all svs items
    imgList = []
    for item in itemList:
        if item['name'].endswith(IMG_TYPE):
            print('image name %s ' % item['name'])
            imgList.append(item['_id'])
            makeLargeImage(gc, item['_id'])

    # now create PATIENT folders inside our new folder
    patientFolderList = []
    patientFolderName = 'Patient%d'
    for i in range(1, 4):
        patientFolder = gc.load_or_create_folder(
            patientFolderName % i, newFolderId, 'folder')
        patientFolderList.append(patientFolder)

    # now let's move an image into the PATIENT1 folder
    patient1Folder = patientFolderList[0]
    patient1FolderId = patient1Folder['_id']

    if imgList:
        srcImageId = imgList[0]
    else:
        raise Exception("There were no images of type %s found" % IMG_TYPE)

    moveParams = {
        'resources': json.dumps({
            'item': [str(srcImageId)]}),
        'parentType': 'folder',
        'parentId': patient1FolderId
    }
    gc.put('resource/move', moveParams)

    # now let us edit the PATIENT1 folder
    patient1MetaData = {'PatientAge': 22, 'PatientDeceased': True}
    gc.addMetadataToFolder(patient1FolderId, patient1MetaData)

    # let us add meta data to the image we moved
    # note how the id remains the same
    newSrcImageMetaData = {'SlideSource': 'FromTCGA', 'SlideType': 'DX'}
    gc.addMetadataToItem(srcImageId, newSrcImageMetaData)

    # find all folders determine if whether each folder is empty or not
    allFolders = recurseGetResource(gc, collectionId, 'folder', 'collection')

    # if the folder size is zero then delete it
    for folder in allFolders:
        if folder['size'] == 0 and not hasItems(gc, folder['_id']):
            # if an empty folder has many child folders
            # then trying to delete one of the children folders after
            # deleting the parent will cause an exception, do not want to exit
            try:
                print('will delete folder %s' % folder['name'])
                gc.delete('folder/%s' % folder['_id'])
            except girder_client.HttpError as err:
                printHttpError(err)
                print('could not delete folder %s' % (folder['name']))

    # already have a list of all items under the designated collection
    # check whether a file under an item is a README.txt
    # if so delete the entire item
    for item in itemList:
        fileIdList = gc.listFile(item['_id'])
        for girderFile in fileIdList:
            if 'readme.txt' == girderFile['name'].lower():
                print('deleting item %s' % item['name'])
                gc.delete('item/%s' % item['_id'])

if __name__ == '__main__':
    try:
        main()
    except girder_client.HttpError as err:
        printHttpError(err)
        print ('exited')
