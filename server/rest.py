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

import os

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import boundHandler, RestException
from girder.utility.progress import ProgressContext

from .datasets.tcga.ingest import ingestTCGA


@describeRoute(
    Description('Import external datasets into Girder.')
    .notes('Only administrators may use this route.')
    .param('dataset', 'The dataset to import.', enum=['tcga'])
    .param('progress', 'Whether to record progress on the operation.',
           required=False, default=True, dataType='boolean')
    .param('assetstoreId', 'Pass this to explicitly bind the imported files'
           ' to a specific filesystem assetstore. If not passed, will use '
           'the normal target assetstore for the given destination.',
           required=False)
    .param('limit', 'If set, limit the import to just this number of files.',
           required=False, dataType='integer')
    .param('localImportPath', 'A local path on the filesystem where the root '
           'ingest path is mirrored. Files found under this path will be '
           'imported (instead of downloaded).', required=False)
)
@access.admin
@boundHandler()
def ingest(self, params):
    self.requireParams(('dataset', 'path'), params)

    dataset = params['dataset']
    if dataset == 'tcga':
        ingestFunc = ingestTCGA
    else:
        raise RestException('Unknown dataset: %s' % dataset)


    progressEnabled = self.boolParam('progress', params, default=True)

    assetstore = \
        self.model('assetstore').load(params['assetstoreId'],
                                      force=True, exc=True) \
        if params.get('assetstoreId') \
        else None

    try:
        limit = int(params['limit'])
    except ValueError:
        raise RestException('Parameter "limit" must be an integer.')
    except KeyError:
        pass

    localImportPath = \
        params['localImportPath'] \
        if params.get('localImportPath') \
        else None
    if localImportPath and not os.path.isdir(localImportPath):
        raise RestException('Directory "%s" not found.' % localImportPath)

    with ProgressContext(
            on=progressEnabled,
            title='Ingesting TCGA data',
            user=self.getCurrentUser()) as p:
        # TODO: progress
        ingestFunc(
            limit=limit,
            assetstore=assetstore,
            localImportPath=localImportPath
        )
