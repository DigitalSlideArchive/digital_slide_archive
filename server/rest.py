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
    .param('limit', 'If not "all", limit the import to just this number of '
           'files.', required=False)
    .param('localImportPath', 'A local path on the filesystem where the root '
           'ingest path is mirrored. Files found under this path will be '
           'imported (instead of downloaded).', required=False)
)
@access.admin
@boundHandler()
def ingest(self, params):
    self.requireParams(('dataset', ), params)

    dataset = params['dataset']
    if dataset != 'tcga':
        raise RestException('Unknown dataset: %s' % dataset)

    progressEnabled = self.boolParam('progress', params, default=True)

    assetstoreId = params.get('assetstoreId') or None
    if assetstoreId:
        # Validate the asssetstore id
        self.model('assetstore').load(params['assetstoreId'],
                                      force=True, exc=True)

    if params.get('limit') == 'all':
        limit = None
    else:
        try:
            limit = int(params['limit'])
            if limit < 1:
                raise ValueError()
        except ValueError:
            raise RestException('Parameter "limit" must be a positive integer '
                                'or "all".')

    localImportPath = \
        params['localImportPath'] \
        if params.get('localImportPath') \
        else None
    if localImportPath and not os.path.isdir(localImportPath):
        raise RestException('Directory "%s" not found.' % localImportPath)

    job = self.model('job', 'jobs').createLocalJob(
        module='girder.plugins.digital_slide_archive.worker',
        function='ingestRunner',
        kwargs={
            'dataset': dataset,
            'progressEnabled': progressEnabled,
            'assetstoreId': assetstoreId,
            'limit': limit,
            'localImportPath': localImportPath
        },
        title='Ingesting TCGA data',
        type='digital_slide_archive.ingest',
        user=self.getCurrentUser(),
        public=False,
        async=True
    )
    self.model('job', 'jobs').scheduleJob(job)
