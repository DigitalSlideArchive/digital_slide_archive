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

import collections
import os
import re
import six

import lxml.html
import requests

from girder.models.model_base import ValidationException
from girder.utility.assetstore_utilities import AssetstoreType, getAssetstoreAdapter
from girder.utility.model_importer import ModelImporter

from .constants import TcgaCodes


# Root path for scraping SVS files
URLBASE = 'https://tcga-data.nci.nih.gov/tcgafiles/ftp_auth/distro_ftpusers/anonymous/tumor/lgg/bcr/nationwidechildrens.org/tissue_images/'


class MetadataParseException(Exception):
    pass


def listAutoIndex(*urlComponents):
    """
    Given a URL to an apache mod_autoindex directory listing, recursively
    scrapes the listing for .svs files. This is a generator that yields each
    such file found in the listing as a tuple whose first element is the URL
    and whose second element is its modified time as reported by the server.
    """
    dirNames = list()
    fileNames = list()

    url = '/'.join(urlComponents)
    if not url.endswith('/'):
        url += '/'

    doc = lxml.html.fromstring(requests.get(url + '?F=2').text)
    rows = doc.xpath('.//table//tr')

    for row in rows:
        name = row.xpath('.//td[2]/a/text()')

        if not name:  # F=2 gives us some header rows that only contain <th>
            continue

        name = name[0].strip()

        if name in {'Parent Directory', 'lost+found/'}:
            continue
        elif name.endswith('/'):  # subdirectory
            dirNames.append(name[:-1])
        else:
            mtime = row.xpath('.//td[3]/text()')[0].strip()
            fileNames.append((name, mtime))

    return dirNames, fileNames


def _getOrCreateIngestUser():
    global ingestUser
    if not ingestUser:
        User = ModelImporter.model('user')
        ingestUser = User.findOne({'login': 'dsa-robot'})
        if not ingestUser:
            ingestUser = User.createUser(
                login='dsa-robot',
                password=None,
                firstName='DSA',
                lastName='Robot',
                email='robot@digitalslidearchive.emory.edu',
                admin=False,
                public=False,
            )
            # Remove default Public / Private folders
            ModelImporter.model('folder').removeWithQuery({
                'parentCollection': 'user',
                'parentId': ingestUser['_id']
            })
    return ingestUser
ingestUser = None


def _getOrCreateCollection(name, description):
    try:
        return collectionCache[name]
    except KeyError:
        Collection = ModelImporter.model('collection')
        collection = Collection.findOne({'name': name})
        if not collection:
            collection = Collection.createCollection(
                name=name,
                creator=_getOrCreateIngestUser(),
                description=description
            )
        collectionCache[name] = collection
        return collection
collectionCache = dict()


def _getOrCreateFolder(name, description, parent, parentType):
    key = (name, parent['_id'])
    try:
        return folderCache[key]
    except KeyError:
        folder = ModelImporter.model('folder').createFolder(
            parent=parent,
            name=name,
            description=description,
            parentType=parentType,
            creator=_getOrCreateIngestUser(),
            reuseExisting=True
        )
        folderCache[key] = folder
        return folder
folderCache = dict()


def _filterMaxBatchRevision(batchDirectories, dataProvider, diseaseStudyCode, dataType):
    batchDirectoriesById = collections.defaultdict(dict)

    for batchDirectory in batchDirectories:
        batchMatch = re.match(
            r'^%s_%s\.%s\.'
            r'(?P<dataLevel>\w+)\.'
            r'(?P<batchId>[0-9]+)\.'
            r'(?P<batchRevision>[0-9]+)\.'
            r'0$' % (
                dataProvider,
                diseaseStudyCode.upper(),
                dataType),
            batchDirectory
        )
        if not batchMatch:
            raise MetadataParseException('Could not parse batch directory: "%s"' % batchDirectory)
        batchMatchDict = batchMatch.groupdict()

        dataLevel = batchMatch.groupdict()['dataLevel']
        if dataLevel != 'Level_1':
            raise MetadataParseException('Unknown data level: "%s"' % dataLevel)
        batchId = int(batchMatchDict['batchId'])
        batchRevision = int(batchMatchDict['batchRevision'])

        batchDirectoriesById[batchId][batchRevision] = batchDirectory

    for batchDirectoriesByRevision in six.viewvalues(batchDirectoriesById):
        batchRevision, batchDirectory = max(six.viewitems(batchDirectoriesByRevision))
        yield batchDirectory


# importBasePath = '/mnt/tcga_mirror/TCGA_RAW/tcga-data.nci.nih.gov/tcgafiles/ftp_auth/distro_ftpusers/anonymous/tumor'


def ingestTCGA(limit=None, downloadNew=True, assetstore=None, localImportPath=None):
    Item = ModelImporter.model('item')

    grCollection = _getOrCreateCollection(
        name='TCGA',
        description='The Cancer Genome Atlas'
    )

    if not assetstore:
        assetstore = ModelImporter.model('upload').getTargetAssetstore(
            modelType='collection',
            resource=grCollection
        )
    if assetstore['type'] != AssetstoreType.FILESYSTEM:
        raise ValidationException(
            'Assetstore "%s" is not a filesystem assetstore.' %
            assetstore['name']
        )
    assetstoreAdapter = getAssetstoreAdapter(assetstore)

    tcgaBaseUrl = 'https://tcga-data.nci.nih.gov/tcgafiles/ftp_auth/distro_ftpusers/anonymous/tumor'

    ingestCount = 0
    for diseaseStudyCode in listAutoIndex(tcgaBaseUrl)[0]:
        if diseaseStudyCode.upper() not in TcgaCodes.DISEASE_STUDIES:
            raise MetadataParseException('Unknown disease study: "%s"' % diseaseStudyCode)

        for repositoryType in listAutoIndex(tcgaBaseUrl, diseaseStudyCode)[0]:
            if repositoryType not in TcgaCodes.REPOSITORY_TYPES:
                raise MetadataParseException('Unknown repository type: "%s"' % repositoryType)
            if repositoryType != 'bcr':
                # Only use 'bcr' now
                continue

            for dataProvider in listAutoIndex(tcgaBaseUrl, diseaseStudyCode, repositoryType)[0]:
                if dataProvider not in TcgaCodes.DATA_PROVIDERS:
                    raise MetadataParseException('Unknown data provider: "%s"' % dataProvider)
                if dataProvider == 'biotab':
                    # Clinical metadata, skip
                    continue
                elif dataProvider == 'supplemental':
                    # Unknown, skip
                    continue

                for dataType in listAutoIndex(
                        tcgaBaseUrl, diseaseStudyCode, repositoryType, dataProvider)[0]:
                    if dataType not in TcgaCodes.DATA_TYPES:
                        raise MetadataParseException('Unknown data type: "%s"' % dataType)
                    if dataType in {'diagnostic_images', 'tissue_images'}:

                        if listAutoIndex(
                                tcgaBaseUrl, diseaseStudyCode, repositoryType,
                                dataProvider, dataType)[0] != ['slide_images']:
                            raise MetadataParseException('Missing sub-directory "slide_images"')

                        for batchDirectory in _filterMaxBatchRevision(
                                listAutoIndex(
                                    tcgaBaseUrl, diseaseStudyCode, repositoryType,
                                    dataProvider, dataType, 'slide_images')[0],
                                dataProvider, diseaseStudyCode, dataType):

                            for slideFileName, modifiedTime in listAutoIndex(
                                    tcgaBaseUrl, diseaseStudyCode, repositoryType, dataProvider,
                                    dataType, 'slide_images', batchDirectory)[1]:
                                if not slideFileName.endswith('.svs'):
                                    continue

                                slideFileUrl = '/'.join([
                                    tcgaBaseUrl, diseaseStudyCode, repositoryType,
                                    dataProvider, dataType, 'slide_images',
                                    batchDirectory, slideFileName])

                                slideBarcodeMatch = re.match(
                                    r'^TCGA-'
                                    r'(?P<TSS>\w{2})-'  # Tissue source site ID
                                    r'(?P<Participant>\w{4})-'  # Study participant
                                    r'(?P<Sample>\d{2})'  # Sample type
                                    r'(?P<Vial>[A-Z])-'  # Order of sample in a sequence of samples
                                    r'(?P<Portion>\d{2})-'  # Order of portion in a sequence of 100 - 120 mg sample portions
                                    r'(?P<SlideLocation>TS|MS|BS|DX)'
                                    r'(?P<SlidePortion>[0-9A-Z]?)\.'
                                    # TODO: UUID should always be uppercase?
                                    r'(?P<UUID>[0-9a-zA-Z]{8}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{12})\.'
                                    r'svs$',
                                    slideFileName
                                )
                                if not slideBarcodeMatch:
                                    print 'Could not parse slide barcode: "%s"' % slideFileUrl
                                    continue
                                    raise MetadataParseException('Could not parse slide barcode: "%s"' % slideFileUrl)
                                slideBarcode = slideBarcodeMatch.groupdict()

                                ingestCount += 1
                                if limit and ingestCount > limit:
                                    global ingestUser
                                    ingestUser = None
                                    collectionCache.clear()
                                    folderCache.clear()
                                    return

                                grDiseaseFolder = _getOrCreateFolder(
                                    name=diseaseStudyCode.upper(),
                                    description=TcgaCodes.DISEASE_STUDIES[diseaseStudyCode.upper()],
                                    parent=grCollection,
                                    parentType='collection'
                                )
                                grPatientFolder = _getOrCreateFolder(
                                    name='TCGA-%s-%s' % (slideBarcode['TSS'], slideBarcode['Participant']),
                                    description='',
                                    parent=grDiseaseFolder,
                                    parentType='folder'
                                )

                                # Get or create item
                                grSlideItem = Item.findOne({
                                    'folderId': grPatientFolder['_id'],
                                    'name': slideBarcode['UUID']
                                })
                                if not grSlideItem:
                                    grSlideItem = Item.createItem(
                                        name=slideBarcode['UUID'],
                                        creator=_getOrCreateIngestUser(),
                                        folder=grPatientFolder,
                                        description=''
                                    )
                                    grSlideItem = Item.setMetadata(
                                        grSlideItem,
                                        slideBarcode
                                    )
                                else:
                                    print 'item already exists: %s' % slideFileUrl

                                # Check if file exists
                                if not grSlideItem['size']:
                                    # File does not exist, import if possible
                                    grSlideFile = None
                                    if localImportPath:
                                        importFilePath = os.path.join(
                                            localImportPath, diseaseStudyCode,
                                            repositoryType, dataProvider, dataType,
                                            'slide_images', batchDirectory, slideFileName)
                                        if os.path.exists(importFilePath):
                                            print 'import found, importing %s' % slideFileUrl
                                            grSlideFile = assetstoreAdapter.importFile(
                                                item=grSlideItem,
                                                path=importFilePath,
                                                user=_getOrCreateIngestUser(),
                                                name=slideFileName,
                                                mimeType='image/x-aperio-svs'
                                            )

                                    # Could not import, download instead
                                    if not grSlideFile and downloadNew:
                                        print 'not found, downloading %s' % slideFileUrl
                                        slideResponse = requests.get(
                                            slideFileUrl,
                                            stream=True
                                        )
                                        grSlideFile = ModelImporter.model('upload').uploadFromFile(
                                            obj=slideResponse.raw,
                                            size=int(slideResponse.headers['Content-Length']),
                                            name=slideFileName,
                                            parentType='item',
                                            parent=grSlideItem,
                                            user=_getOrCreateIngestUser(),
                                            mimeType='image/x-aperio-svs'
                                        )

                                    if grSlideFile:
                                        # The addition of a file changed the size of the item, so reload it
                                        grSlideItem = Item.findOne({'_id': grSlideItem['_id']})
                                        # Mark as a large_image
                                        ModelImporter.model('image_item', 'large_image').createImageItem(
                                            item=grSlideItem,
                                            fileObj=grSlideFile,
                                            user=_getOrCreateIngestUser(),
                                            # TODO: token
                                        )
                                    else:
                                        print 'not imported %s' % slideFileUrl
                                        continue
                                else:
                                    print 'file already exists: %s' % slideFileUrl

                                # TODO: fix creation / updated dates (for everyone first)
                    else:
                        continue

    global ingestUser
    ingestUser = None
    collectionCache.clear()
    folderCache.clear()

