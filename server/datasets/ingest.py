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

import datetime
import email.utils
import os
import six

import girder
from girder.constants import SettingKey
from girder.models.model_base import ValidationException
from girder.utility.assetstore_utilities import AssetstoreType, \
    getAssetstoreAdapter
from girder.utility.model_importer import ModelImporter


class IngestException(Exception):
    pass


class Path(tuple):
    def __new__(cls, *args):
        if isinstance(args[0], Path):
            args = args[0] + args[1:]
        return super(Path, cls).__new__(cls, args)

    def __str__(self):
        return self.join()

    def join(self):
        return os.path.join(*self)

    def tail(self):
        return self[-1]

    def push(self, tail):
        return type(self)(self, tail)


class Ingest(object):
    def __init__(self, limit, collection, assetstore=None, job=None,
                 notify=True):
        """
        Create a new data ingest instance.

        :param limit: The number of items to ingest, or None for unlimited.
        :type limit: int or None
        :param collection: The collection to store ingested files in.
        :param assetstore: An optional assetstore to store downloaded files in.
                           Defaults to using the collection-default assetstore.
        :param job: An optional job to log and send notifications to.
        :param notify: If a job is provided, determines if notifications will be
                       sent.
        """
        self.limit = limit
        self.ingestCount = 0

        self.collection = collection

        self.assetstore = assetstore
        if not self.assetstore:
            self.assetstore = ModelImporter.model('upload').getTargetAssetstore(
                modelType='collection',
                resource=self.collection
            )
        if self.assetstore['type'] != AssetstoreType.FILESYSTEM:
            raise ValidationException(
                'Assetstore "%s" is not a filesystem assetstore.' %
                self.assetstore['name']
            )
        self.assetstoreAdapter = getAssetstoreAdapter(self.assetstore)

        self.job = job
        self.notify = notify

        # Set up cache
        self.ingestUser = None
        self.folderCache = dict()

    def _log(self, *args):
        if len(args) > 1:
            msg = ' '.join([str(item) for item in args])
        else:
            msg = str(args[0])
        girder.logger.info(msg)

    def _updateProgress(self, messageExtension='', marginalValue=0.0):
        if not self.job:
            return
        ModelImporter.model('job', 'jobs').updateJob(
            job=self.job,
            notify=self.notify,
            progressTotal=self.limit if self.limit else 0,
            progressCurrent=self.ingestCount + marginalValue,
            progressMessage='Ingesting items (%s)%s' % (
                ('%d done' % self.ingestCount)
                if not self.limit
                else ('%d left' % (self.limit - self.ingestCount)),
                messageExtension
            )
        )

    def _getOrCreateIngestUser(self):
        if not self.ingestUser:
            User = ModelImporter.model('user')
            self.ingestUser = User.findOne({'login': 'dsa-robot'})
            if not self.ingestUser:
                self.ingestUser = User.createUser(
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
                    'parentId': self.ingestUser['_id']
                })
        return self.ingestUser

    def _getOrCreateCollection(self, name, description):
        Collection = ModelImporter.model('collection')
        collection = Collection.findOne({'name': name})
        if not collection:
            collection = Collection.createCollection(
                name=name,
                creator=self._getOrCreateIngestUser(),
                description=description
            )
        return collection

    def _getOrCreateFolder(self, name, description, parent, parentType):
        key = (name, parent['_id'])
        try:
            return self.folderCache[key]
        except KeyError:
            folder = ModelImporter.model('folder').createFolder(
                parent=parent,
                name=name,
                description=description,
                parentType=parentType,
                creator=self._getOrCreateIngestUser(),
                reuseExisting=True
            )
            self.folderCache[key] = folder
            return folder

    @staticmethod
    def _httpDateToDatetime(httpDate):
        return datetime.datetime(*email.utils.parsedate(httpDate)[:6])

    def _uploadWithProgress(self, obj, **kwargs):
        Upload = ModelImporter.model('upload')
        if not (self.job and self.notify):
            # If notifications are disabled, there is no need to log marginal
            # upload progress
            return Upload.uploadFromFile(obj, **kwargs)

        upload = Upload.createUpload(**kwargs)
        dataRead = 0
        chunkSize = max(ModelImporter.model('setting').get(
            SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE), 32 * 1024**2)
        while True:
            self._updateProgress(
                messageExtension='  %3.1f%% transferred of next item' %
                                 (100.0 * dataRead / kwargs['size']),
                marginalValue=(float(dataRead) / kwargs['size'])
            )
            data = obj.read(chunkSize)
            if not data:
                break
            upload = Upload.handleChunk(upload, six.BytesIO(data))
            dataRead += len(data)
        self._updateProgress(
            messageExtension='  100%% transferred of next item',
            marginalValue=1.0
        )
        return upload
