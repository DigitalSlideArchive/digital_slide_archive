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

from girder.utility.model_importer import ModelImporter

from ..ingest import Ingest, Path, IngestException
from .constants import TcgaCodes


class TCGAPath(Path):
    @property
    def diseaseStudyCode(self):
        return self[1]

    @property
    def repositoryType(self):
        return self[2]

    @property
    def dataProvider(self):
        return self[3]

    @property
    def dataType(self):
        return self[4]


class TCGAIngest(Ingest):
    BASE_URL = 'https://tcga-data.nci.nih.gov/tcgafiles/ftp_auth/distro_ftpusers/anonymous/tumor'

    def __init__(self, limit, assetstore=None, progress=None,
                 downloadNew=True, localImportPath=None):
        # Create 'ingestUser' to avoid circular logic
        self.ingestUser = None
        collection = self._getOrCreateCollection(
            name='TCGA',
            description='The Cancer Genome Atlas'
        )

        super(TCGAIngest, self).__init__(
            limit, collection, assetstore, progress)

        self.downloadNew = downloadNew
        self.localImportPath = localImportPath

    @staticmethod
    def _listAutoIndex(urlPath):
        """
        Given a URL to an apache mod_autoindex directory listing, recursively
        scrapes the listing for .svs files. This is a generator that yields each
        such file found in the listing as a tuple whose first element is the URL
        and whose second element is its modified time as reported by the server.

        type urlPath: Path
        rtype: (list[Path], list[(Path, str)])
        """
        dirPaths = list()
        filePaths = list()

        url = urlPath.join()
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
                dirPaths.append(urlPath.push(name[:-1]))
            else:
                mtime = row.xpath('.//td[3]/text()')[0].strip()
                filePaths.append((urlPath.push(name), mtime))

        return dirPaths, filePaths

    @staticmethod
    def _filterMaxBatchRevision(batchDirectoryPaths):
        batchDirectoryPathsByRevisionById = collections.defaultdict(dict)

        for batchDirectoryPath in batchDirectoryPaths:
            batchMatch = re.match(
                r'^%s_%s\.%s\.'
                r'(?P<dataLevel>\w+)\.'
                r'(?P<batchId>[0-9]+)\.'
                r'(?P<batchRevision>[0-9]+)\.'
                r'0$' % (
                    batchDirectoryPath.dataProvider,
                    batchDirectoryPath.diseaseStudyCode.upper(),
                    batchDirectoryPath.dataType),
                batchDirectoryPath.tail()
            )
            if not batchMatch:
                raise IngestException('Could not parse batch directory: "%s"' % str(batchDirectoryPath))
            batchMatchDict = batchMatch.groupdict()

            dataLevel = batchMatch.groupdict()['dataLevel']
            if dataLevel != 'Level_1':
                raise IngestException('Unknown data level: "%s"' % str(batchDirectoryPath))
            batchId = int(batchMatchDict['batchId'])
            batchRevision = int(batchMatchDict['batchRevision'])

            batchDirectoryPathsByRevisionById[batchId][batchRevision] = batchDirectoryPath

        for batchDirectoryPathsByRevision in six.viewvalues(batchDirectoryPathsByRevisionById):
            batchRevision, batchDirectoryPath = max(six.viewitems(batchDirectoryPathsByRevision))
            yield batchDirectoryPath

    @staticmethod
    def _getSlideMetadata(slideFilePath):
        slideFileName = slideFilePath.tail()

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
            raise IngestException('Could not parse slide barcode: "%s"' % str(slideFilePath))
        slideMetadata = slideBarcodeMatch.groupdict()

        slideMetadata['DiseaseStudy'] = slideFilePath[1]
        slideMetadata['RepositoryType'] = slideFilePath[2]
        slideMetadata['DataProvider'] = slideFilePath[3]
        slideMetadata['DataType'] = slideFilePath[4]

        return slideMetadata

    def _ingestSlide(self, slideFilePath):
        Item = ModelImporter.model('item')

        slideFileName = slideFilePath.tail()

        slideMetadata = self._getSlideMetadata(slideFilePath)

        grDiseaseFolder = self._getOrCreateFolder(
            name=slideMetadata['DiseaseStudy'].upper(),
            description=TcgaCodes.DISEASE_STUDIES[slideMetadata['DiseaseStudy'].upper()],
            parent=self.collection,
            parentType='collection'
        )
        grPatientFolder = self._getOrCreateFolder(
            name='TCGA-%s-%s' % (slideMetadata['TSS'], slideMetadata['Participant']),
            description='',
            parent=grDiseaseFolder,
            parentType='folder'
        )

        self._log('Ingesting image: %s' % str(slideFilePath))

        # Get or create item
        grSlideItem = Item.findOne({
            'folderId': grPatientFolder['_id'],
            'name': slideMetadata['UUID']
        })
        if not grSlideItem:
            self._log('  Creating item')
            grSlideItem = Item.createItem(
                name=slideMetadata['UUID'],
                creator=self._getOrCreateIngestUser(),
                folder=grPatientFolder,
                description=''
            )
            grSlideItem = Item.setMetadata(
                grSlideItem,
                slideMetadata
            )
        else:
            self._log('  Item already exists')

        # Check if file exists
        if not grSlideItem['size']:
            self._log('  File does not exist')

            # Import if possible
            grSlideFile = None
            if self.localImportPath:
                localImportSlideFilePath = Path(self.localImportPath, *slideFilePath[1:])
                if os.path.exists(localImportSlideFilePath.join()):
                    self._log('  File found for local import at: %s' % str(localImportSlideFilePath))
                    grSlideFile = self.assetstoreAdapter.importFile(
                        item=grSlideItem,
                        path=localImportSlideFilePath.join(),
                        user=self._getOrCreateIngestUser(),
                        name=slideFileName,
                        mimeType='image/x-aperio-svs'
                    )
                    self._log('  Local import complete')
                else:
                    self._log('  File not found for local import at: %s' % str(localImportSlideFilePath))

            # Could not import, download instead
            if not grSlideFile and self.downloadNew:
                self._log('  Downloading file')
                slideResponse = requests.get(slideFilePath.join(), stream=True)
                grSlideFile = self._uploadWithProgress(
                    obj=slideResponse.raw,
                    size=int(slideResponse.headers['Content-Length']),
                    name=slideFileName,
                    parentType='item',
                    parent=grSlideItem,
                    user=self._getOrCreateIngestUser(),
                    mimeType='image/x-aperio-svs'
                )
                self._log('  Download complete')
            else:
                # Get just the HTTP headers for later use
                slideResponse = requests.head(slideFilePath.join())

            if grSlideFile:
                self._log('  Setting internal metadata')
                # The addition of a file changed the size of the item, so reload it
                grSlideItem = Item.findOne({'_id': grSlideItem['_id']})

                # Attempt to mirror the upstream creation date
                if 'Last-Modified' in slideResponse.headers:
                    grSlideItem['created'] = grSlideFile['created'] = \
                        self._httpDateToDatetime(
                            slideResponse.headers['Last-Modified'])
                    grSlideFile = ModelImporter.model('file').save(grSlideFile)
                    # 'createImageItem' will save the item

                # Mark as a large_image
                try:
                    ModelImporter.model('image_item', 'large_image').createImageItem(
                        item=grSlideItem,
                        fileObj=grSlideFile,
                        user=self._getOrCreateIngestUser(),
                        # TODO: token
                        token=None
                    )
                except Exception as e:
                    # TODO: remove this, large_image creation should not normally fail
                    # (though the job may eventually fail once started)
                    self._log('  ERROR: large_image creation failed: %s' % str(e))
            else:
                self._log('  File not ingested')
        else:
            self._log('  File already exists')

    def _setFolderTimes(self):
        Collection = ModelImporter.model('collection')
        Folder = ModelImporter.model('folder')
        Item = ModelImporter.model('item')
        earliestCollectionTime = self.collection['created']
        for grDiseaseFolder in Folder.find({'parentId': self.collection['_id']}):
            earliestDiseaseTime = grDiseaseFolder['created']
            for grPatientFolder in Folder.find({'parentId': grDiseaseFolder['_id']}):
                earliestItemQuery = Item.collection.aggregate([
                    {'$match': {'folderId': grPatientFolder['_id']}},
                    {'$group': {
                        '_id': None,
                        'earliest': {'$min': '$created'}
                    }}
                ])
                earliestPatientTime = earliestItemQuery.next()['earliest']
                Folder.update(
                    {'_id': grPatientFolder['_id']},
                    {'$set': {'created': earliestPatientTime}}
                )
                earliestDiseaseTime = min(earliestPatientTime, earliestDiseaseTime)
            Folder.update(
                {'_id': grDiseaseFolder['_id']},
                {'$set': {'created': earliestDiseaseTime}}
            )
            earliestCollectionTime = min(earliestDiseaseTime, earliestCollectionTime)
        Collection.update(
            {'_id': self.collection['_id']},
            {'$set': {'created': earliestCollectionTime}}
        )

    def _ingestData(self):
        self.ingestCount = 0

        basePath = TCGAPath(self.BASE_URL)
        for diseaseStudyPath in self._listAutoIndex(basePath)[0]:
            if diseaseStudyPath.diseaseStudyCode.upper() not in TcgaCodes.DISEASE_STUDIES:
                raise IngestException('Unknown disease study: "%s"' % str(diseaseStudyPath))

            for repositoryPath in self._listAutoIndex(diseaseStudyPath)[0]:
                if repositoryPath.repositoryType not in TcgaCodes.REPOSITORY_TYPES:
                    raise IngestException('Unknown repository type: "%s"' % str(repositoryPath))
                if repositoryPath.repositoryType != 'bcr':
                    # Only use 'bcr' now
                    continue

                for providerPath in self._listAutoIndex(repositoryPath)[0]:
                    if providerPath.dataProvider not in TcgaCodes.DATA_PROVIDERS:
                        raise IngestException('Unknown data provider: "%s"' % str(providerPath))
                    if providerPath.dataProvider == 'biotab':
                        # Clinical metadata, skip
                        continue

                    for dataTypePath in self._listAutoIndex(providerPath)[0]:
                        if dataTypePath.dataType not in TcgaCodes.DATA_TYPES:
                            raise IngestException('Unknown data type: "%s"' % str(dataTypePath))
                        if dataTypePath.dataType in {'diagnostic_images', 'tissue_images'}:
                            dataTypeSubPaths = self._listAutoIndex(dataTypePath)[0]
                            if len(dataTypeSubPaths) != 1:
                                raise IngestException('Unexpected sub-directory at: %s' % str(dataTypePath))
                            if dataTypeSubPaths[0].tail() != 'slide_images':
                                raise IngestException('Missing sub-directory "slide_images" at: %s' % str(dataTypePath))
                            dataTypeSubPath = dataTypeSubPaths[0]

                            for batchPath in self._filterMaxBatchRevision(self._listAutoIndex(dataTypeSubPath)[0]):

                                for slideFilePath, modifiedTime in self._listAutoIndex(batchPath)[1]:
                                    if not slideFilePath.tail().endswith('.svs'):
                                        continue
                                    try:
                                        self._ingestSlide(slideFilePath)
                                    except IngestException as e:
                                        # Failures of single slides should not be fatal
                                        self._log(str(e))
                                    else:
                                        self.ingestCount += 1
                                        self._updateProgress()
                                    if self.limit and self.ingestCount >= self.limit:
                                        return
                        else:
                            # Other data types will be handled here
                            continue

    def ingest(self):
        self._updateProgress()
        self._ingestData()
        self._setFolderTimes()
        self._updateProgress()
