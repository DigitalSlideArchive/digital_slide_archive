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

import six

from girder.api import access
from girder.api.describe import Description, describeRoute, autoDescribeRoute
from girder.api.rest import boundHandler, RestException, filtermodel
from girder.api.v1.resource import Resource as ResourceResource
from girder.constants import AccessType, TokenScope
from girder.models.folder import Folder
from girder.models.item import Item
from girder.utility.model_importer import ModelImporter


def addSystemEndpoints(apiRoot):
    """
    This adds endpoints to routes that already exist in Girder.

    :param apiRoot: Girder api root class.
    """
    # Added to the item route
    apiRoot.item.route('GET', ('query',), getItemsByQuery)
    DSAResourceResource(apiRoot)


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
    for folder in Folder().childFolders(
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
        if parentType == 'folder':
            kwargs = kwargs.copy()
            kwargs['includeVirtual'] = True
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
    for folder in Folder().childFolders(
            parentType=parentType, parent=parent, user=user,
            limit=0, offset=0, sort=sort, **kwargs):
        if _internal['done']:
            return
        for item in allChildItems(folder, 'folder', user, sort=sort,
                                  _internal=_internal, **kwargs):
            yield item


@access.public(scope=TokenScope.DATA_READ)
@filtermodel(model=Item)
@autoDescribeRoute(
    Description('List items that match a query.')
    .responseClass('Item', array=True)
    .jsonParam('query', 'Find items that match this Mongo query.',
               required=True, requireObject=True)
    .pagingParams(defaultSort='_id')
    .errorResponse()
)
@boundHandler()
def getItemsByQuery(self, query, limit, offset, sort):
    user = self.getCurrentUser()
    return Item().findWithPermissions(query, offset=offset, limit=limit, sort=sort, user=user)


class DSAResourceResource(ResourceResource):
    def __init__(self, apiRoot):
        super(ResourceResource, self).__init__()
        # Added to the resource route
        apiRoot.resource.route('GET', (':id', 'items'), self.getResourceItems)
        apiRoot.resource.route('PUT', ('metadata',), self.putResourceMetadata)

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
    def getResourceItems(self, id, params):
        user = self.getCurrentUser()
        modelType = params['type']
        model = ModelImporter.model(modelType)
        doc = model.load(id=id, user=user, level=AccessType.READ)
        if not doc:
            raise RestException('Resource not found.')
        limit, offset, sort = self.getPagingParameters(params, '_id')
        return list(allChildItems(
            parentType=modelType, parent=doc, user=user,
            limit=limit, offset=offset, sort=sort))

    @autoDescribeRoute(
        Description('Set metadata on multiple resources at once.')
        .jsonParam('resources', 'A JSON-encoded set of resources to modify.  '
                   'Each type is a list of ids. For example: {"item": [(item '
                   'id 1), (item id 2)], "folder": [(folder id 1)]}.',
                   requireObject=True)
        .jsonParam('metadata', 'A JSON object containing the metadata keys to '
                   'add', paramType='body', requireObject=True)
        .param('allowNull', 'Whether "null" is allowed as a metadata value.',
               required=False, dataType='boolean', default=False)
        .errorResponse('Unsupported or unknown resource type.')
        .errorResponse('Invalid resources format.')
        .errorResponse('No resources specified.')
        .errorResponse('Resource not found.')
        .errorResponse('Write access was denied for a resource.', 403)
    )
    @access.public
    def putResourceMetadata(self, resources, metadata, allowNull):
        user = self.getCurrentUser()
        self._validateResourceSet(resources)
        # Validate that we have write permission for all resources; if any
        # fail, no item will be changed.
        for kind in resources:
            model = self._getResourceModel(kind, 'setMetadata')
            for id in resources[kind]:
                model.load(id=id, user=user, level=AccessType.WRITE)
        metaUpdate = {}
        for key, value in six.iteritems(metadata):
            if value is None and not allowNull:
                metaUpdate.setdefault('$unset', {})['meta.' + key] = ''
            else:
                metaUpdate.setdefault('$set', {})['meta.' + key] = value
        modified = 0
        for kind in resources:
            model = self._getResourceModel(kind, 'setMetadata')
            for id in resources[kind]:
                resource = model.load(id=id, user=user, level=AccessType.WRITE)
                # We aren't using model.setMetadata, since it is more
                # restrictive than we want.
                modified += model.update({'_id': resource['_id']}, metaUpdate).modified_count
        return modified
