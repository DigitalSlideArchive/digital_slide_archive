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

import girder_client
from girder_client import HttpError
import json


def print_http_error(err):
    print ('Request Error:\nstatus:%s\nresponse%s\nurl:%s'
           '\nmethod:%s ' % (err.status, err.responseText, err.url, err.method))


def recurse_get_resource(client, parentFolder, resourceType,
                         parentType='folder'):
    # now get all folders
    folders = None
    folderIdList = None
    resourceList = []
    try:
        folders = client.listFolder(parentFolder, parentFolderType=parentType)
    except HttpError as err:
        print_http_error(err)
        return []
    folderIdList = get_field(folders, '_id')

    if resourceType is 'item' and parentType is not 'collection':
        try:
            data = client.listItem(parentFolder)

            resourceList.extend(data)
        except HttpError as err:
            print_http_error(err)
            return []
    elif resourceType is 'folder':
        resourceList.extend(folders)
    elif resourceType is not 'item' and resourceType is not 'folder':
        return []
    for folderId in folderIdList:
        resourceList.extend(
            recurse_get_resource(client, folderId,
                                 resourceType))
    return resourceList


def print_field(data, strKey):
    for i in range(len(data)):
        print(data[i][strKey])


def get_field(data, strKey):
    return [i[strKey] for i in data]


def make_large_image(girderClient, file_id):
    # first check if the file is already a large image
    item_data = None
    try:
        item_data = girderClient.getItem(file_id)
    except HttpError as err:
        print_http_error(err)
        print('bad item id ')
    # if the item is already a large image return

    if 'largeImage' in item_data:
        return
    try:
        girderClient.post('item/%s/tiles' % file_id)
    except HttpError as err:
        print_http_error(err)


def isEmpty(girderClient, folder):
    itemList = recurse_get_resource(girderClient, folder, 'item',)
    if len(itemList) == 0:
        return True
    else:
        return False

girderLocation = 'http://localhost:8080/api/v1'

collectionName = 'DG TCGA'
collectionId = None

collection_data = None

new_folder_name = 'GBM'
newFolderId = None

img_type = '.jpeg'


def main():
    # login to girder, you will be prompted for credentials
    gc = girder_client.GirderClient(apiUrl=girderLocation)
    gc.authenticate(interactive=True)

    # get the id of the desired collection

    request_url = 'resource/lookup?path=collection/%s' % (collectionName)
    collection_data = gc.getResource(request_url)

    collectionId = collection_data['_id']
    newFolderData = None

    # create a folder under this collection or
    # load a preexisting folder that exists with the same name and parent

    newFolderData = gc.load_or_create_folder(new_folder_name,
                                             collectionId, 'collection')
    newFolderId = newFolderData['_id']

    # get a list of all items within each folder of the collection
    itemList = recurse_get_resource(gc, collectionId, 'item', 'collection')

    tempImageId = None
    print('Listing all %s items in the collection %s' % (img_type,
                                                         collectionName))
    # create a list to store id of all svs items
    img_list = []
    for item in itemList:
        if img_type in item['name']:
            tempImageId = item['_id']
            print('image name %s ' % (item['name']))
            img_list.append(tempImageId)
            make_large_image(gc, tempImageId)

    # now create PATIENT folders inside our new folder

    patientFolderList = []
    patient_folder_name = 'Patient%d'

    for i in range(1, 4):
        tempName = patient_folder_name % (i)

        patientFolderList.append(
                gc.load_or_create_folder(tempName, newFolderId, 'folder'))

    # now let us move an image into the PATIENT1 folder

    patient1Folder = patientFolderList[0]
    patient1FolderId = patient1Folder['_id']

    srcImageId = img_list[0]

    moveParams = {
        'resources': json.dumps({
            'item': [str(srcImageId)]}),
        'parentType': 'folder',
        'parentId': patient1FolderId
    }

    try:
        gc.put('resource/move', moveParams)
    except HttpError as err:
        print_http_error(err)
        print ('exited')
        exit()

    # now let us edit the PATIENT1 folder

    patient1MetaData = {'PatientAge': 22, 'PatientDeceased': True}

    try:
        gc.addMetadataToFolder(patient1FolderId, patient1MetaData)
    except HttpError as err:
        print_http_error(err)
        print ('exited')
        exit()

    # let us add meta data to the image we moved
    # note how the id remains the same
    newSrcImageMetaData = {'SlideSource': 'FromTCGA', 'SlideType': 'DX'}
    try:
        gc.addMetadataToItem(srcImageId, newSrcImageMetaData)
    except HttpError as err:
        print_http_error(err)
        print ('exited')
        exit()

    # find all folders determine if whether each folder is empty or not
    allFolders = []

    allFolders = recurse_get_resource(gc, collectionId,
                                      'folder', 'collection')

    # if the folder size is zero then delete it
    for folder in allFolders:

        if folder['size'] == 0 and isEmpty(gc, folder['_id']):
            try:
                print('will delete folder %s' % folder['name'])

                gc.delete('folder/%s' % folder['_id'])

            except HttpError as err:
                print_http_error(err)
                print('could not delete folder %s' % (folder['name']))
                print ('exited')
                exit()
    # already have a list of all items under the designated collection
    # check whether a file under an item is a README.txt
    # if so delete the entire item
    for item in itemList:
        fileIdList = gc.listFile(item['_id'])
        for girder_file in fileIdList:
            if 'README.txt' in girder_file['name']:
                print('deleting item %s' % item['name'])
                try:
                    gc.delete('item/%s' % item['_id'])
                except HttpError as err:
                    print_http_error(err)
                    print('could not delete item %s' % (item['name']))
                    print ('exited')
                    exit()

if __name__ == '__main__':
    try:
        main()
    except HttpError as err:
        print_http_error(err)
        print ('exited')
