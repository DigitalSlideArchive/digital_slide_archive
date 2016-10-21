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
from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter


def addSystemEndpoints(apiRoot):
    """
    This adds endpoints to routes that already exist in Girder.

    :param apiRoot: Girder api root class.
    """
    # Added to the resource route
    apiRoot.resource.route('GET', (':id', 'items'), getResourceItems)
    # Added to the system route
    apiRoot.system.route('POST', ('ingest',), ingest)


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


def allChildFolders(parent, parentType, user, limit=0, offset=0,
                    sort=None, _internal=None, **kwargs):
    """
    This generator will yield all folders that are children of the resource
    or recursively children of child folders of the resource, with access
    policy filtering.  Passes any kwargs to the find function.

    :param parent: The parent object.
    :type parentType: Type of the parent object.
    :param parentType: The parent type.
    :type parentType: 'user', 'folder', or 'collection'
    :param user: The user running the query.  Only returns folders that this
                 user can see.
    :param limit: Result limit.
    :param offset: Result offset.
    :param sort: The sort structure to pass to pymongo.  Child folders are
        served depth first, and this sort is applied within the resource
        and then within each child folder.
    """
    if _internal is None:
        _internal = {
            'limit': limit,
            'offset': offset,
            'done': False
        }
    for folder in ModelImporter.model('folder').childFolders(
            parentType=parentType, parent=parent, user=user,
            limit=_internal['limit'], offset=0, sort=sort, **kwargs):
        if _internal['done']:
            return
        if _internal['offset']:
            _internal['offset'] -= 1
        else:
            yield folder
            if _internal['limit']:
                _internal['limit'] -= 1
                if not _internal['limit']:
                    _internal['done'] = True
                    return
        for childFolder in allChildFolders(
                folder, 'folder', user, sort=sort, _internal=_internal,
                **kwargs):
            yield childFolder


def allChildItems(parent, parentType, user, limit=0, offset=0,
                  sort=None, _internal=None, **kwargs):
    """
    This generator will yield all items that are children of the resource
    or recursively children of child folders of the resource, with access
    policy filtering.  Passes any kwargs to the find function.

    :param parent: The parent object.
    :type parentType: Type of the parent object.
    :param parentType: The parent type.
    :type parentType: 'user', 'folder', or 'collection'
    :param user: The user running the query. Only returns items that this
                 user can see.
    :param limit: Result limit.
    :param offset: Result offset.
    :param sort: The sort structure to pass to pymongo.  Child folders are
        served depth first, and this sort is applied within the resource
        and then within each child folder.  Child items are processed
        before child folders.
    """
    if _internal is None:
        _internal = {
            'limit': limit,
            'offset': offset,
            'done': False
        }
    model = ModelImporter.model(parentType)
    if hasattr(model, 'childItems'):
        for item in model.childItems(
                parent, user=user,
                limit=_internal['limit'] + _internal['offset'],
                offset=0, sort=sort, **kwargs):
            if _internal['offset']:
                _internal['offset'] -= 1
            else:
                yield item
                if _internal['limit']:
                    _internal['limit'] -= 1
                    if not _internal['limit']:
                        _internal['done'] = True
                        return
    for folder in ModelImporter.model('folder').childFolders(
            parentType=parentType, parent=parent, user=user,
            limit=0, offset=0, sort=sort, **kwargs):
        if _internal['done']:
            return
        for item in allChildItems(folder, 'folder', user, sort=sort,
                                  _internal=_internal, **kwargs):
            yield item


@describeRoute(
    Description('Get all of the items that are children of a resource.')
    .param('id', 'The ID of the resource.', paramType='path')
    .param('type', 'The type of the resource (folder, collection, or '
           'user).')
    .pagingParams(defaultSort='_id')
    .errorResponse('ID was invalid.')
    .errorResponse('Access was denied for the resource.', 403)
)
@access.public
@boundHandler()
def getResourceItems(self, id, params):
    user = self.getCurrentUser()
    modelType = params['type']
    model = self.model(modelType)
    doc = model.load(id=id, user=user, level=AccessType.READ)
    if not doc:
        raise RestException('Resource not found.')
    limit, offset, sort = self.getPagingParameters(params, '_id')
    return list(allChildItems(
        parentType=modelType, parent=doc, user=user,
        limit=limit, offset=offset, sort=sort))
