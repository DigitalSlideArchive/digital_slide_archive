# How to add a new endpoint:
# 1. Add the route in the __init__ method.  See
# http://girder.readthedocs.io/en/latest/plugin-development.html?highlight=route
#    for details.
# 2. Add a new method to the DSAEndpointsResource class.  If it has a
#    @describeRoute decorator, it will show up in the Swagger API.

from bson.errors import InvalidId
from bson.objectid import ObjectId

from girder import logger
from girder.api import access
from girder.api.describe import describeRoute, autoDescribeRoute, Description
from girder.api.rest import Resource, RestException
from girder.constants import AccessType
from girder.models import model_base
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User
from girder.utility import model_importer

from .system import allChildFolders, allChildItems


def _getModelType(id):
    """
    Given any Mongo ID, return the corresponding Girder model name that it is
    associated with.

    :param id: a Mongo id either as a string or ObjectId.
    :returns: the Girder model name for a core model, the (name, plugin) for a
        plugin model, or None if the id is not found in any registered model.
    """
    if not isinstance(id, ObjectId):
        try:
            id = ObjectId(id)
        except InvalidId:
            return None
    for model in model_base._modelSingletons:
        if hasattr(model, 'findOne'):
            if model.findOne({'_id': id}, fields=['_id']):
                for plugin in model_importer._modelInstances:
                    if model in model_importer._modelInstances[plugin]:
                        return (model.name, plugin)
                return model.name
    return None


class DSAEndpointsResource(Resource):

    def __init__(self):
        super(DSAEndpointsResource, self).__init__()

        self.resourceName = 'dsa_endpoints'
        self.route('GET', ('child_metadata', ':id'), self.getChildMetadata)
        self.route('GET', ('browse', ), self.browseTreeRoot)
        self.route('GET', ('browse', ':id'), self.browseTreeById)

    @describeRoute(
        Description('Get all metadata for a resource and all folders and '
                    'items that are children of a resource.')
        .param('id', 'The ID of the resource.', paramType='path')
        .param('type', 'The type of the resource (folder, collection, or '
               'user).')
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the resource.', 403)
    )
    @access.public
    def getChildMetadata(self, id, params):
        user = self.getCurrentUser()
        modelType = params['type']
        model = self.model(modelType)
        doc = model.load(id=id, user=user, level=AccessType.READ)
        if not doc:
            raise RestException('Resource not found.')
        results = {}
        if doc.get('meta'):
            results[str(doc['_id'])] = doc['meta']
        logger.info('Getting child metadata')
        for folder in allChildFolders(parentType=modelType, parent=doc,
                                      user=user, limit=0, offset=0):
            if folder.get('meta'):
                results[str(folder['_id'])] = folder['meta']
        for item in allChildItems(parentType=modelType, parent=doc,
                                  user=user, limit=0, offset=0):
            if item.get('meta'):
                results[str(item['_id'])] = item['meta']
        return results

    def _browseTree(self, user, id=None, depth=1,
                    limit=0, offset=0, sort=None, fields=[], **kwargs):
        """
        Get the users, collections, folders, items, and files of the specified
        document, recursing to a specified depth.

        :param user: the user that authenticates the process.  The user must
            have read access on each returned resource.
        :param id: the id of a folder, user, or collection.  None to return an
            object that lists users and collections.
        :param depth: depth to recurse information.
        :param limit: maximum number of each type of resource to obtain.
        :param offset: offset for each type of resource.
        :param sort: default sort order.  This is an array of tuples of
            (index name, direction).  If the first index name is 'name' or
            'lowerName', and users are part of the returned information, users
            will be sorted by login.
        :param fields: extra fields to return.
        :returns: an object with 'doc': the document associated with the ID,
            'type': the resource type of the document, 'limit': the limit used
            in queries, 'offset': the offset used in queries, 'sort': the sort
            used in queries, and a set, as available, of 'user', 'collection',
            'folder', 'item', each of which contains a list as returned by this
            function, and 'file' with a direct list of files.  If present, each
            of these has an associated 'user_count', 'collection_count',
            'folder_count', 'item_count', 'file_count' with the total number of
            records for that resource type.
        """
        # Need to implement fields, filterResultsByPermission
        result = {'offset': offset, 'limit': limit, 'sort': sort}
        children = {}
        doc = None
        if not id:
            user_sort = sort[:]
            if user_sort[0][0] in ('name', 'lowerName'):
                user_sort[0] = ['login', sort[0][1]]
            users = User().find(user=user, offset=offset, limit=limit, sort=user_sort)
            children['user'] = list(users)
            result['user_count'] = users.count()
            collections = Collection().find(user=user, offset=offset, limit=limit, sort=sort)
            children['collection'] = list(collections)
            result['collection_count'] = collections.count()
        else:
            modelType = _getModelType(id)
            if modelType and not isinstance(modelType, tuple):
                doc = model_importer.ModelImporter.model(modelType).load(
                    id, level=AccessType.READ, user=user)
            if doc:
                doc['_modelType'] = modelType
            if doc:
                result['doc'] = doc
                result['type'] = doc['_modelType']
        if doc:
            if doc['_modelType'] != 'item':
                #  This is the correct action when filterResultsByPermission
                #  uses a query, but until then we just perfom the bare query
                # folders = Folder().childFolders(
                #     parent=doc, parentType=doc['_modelType'], user=user,
                #     limit=limit, offset=offset, sort=sort)
                folders = Folder().find(
                    {'parentId': doc['_id'], 'parentCollection': doc['_modelType']},
                    limit=limit, offset=offset, sort=sort)
                children['folder'] = list(folders)
                result['folder_count'] = folders.count()
                if doc['_modelType'] == 'folder':
                    items = Folder().childItems(doc, limit=limit, offset=offset, sort=sort)
                    children['item'] = list(items)
                    result['item_count'] = items.count()
            else:
                files = Item().childFiles(doc, limit=limit, offset=offset, sort=sort)
                result['file'] = list(files)
                result['file_count'] = files.count()
        if depth >= 1:
            for type in ('user', 'collection', 'folder', 'item'):
                for subdoc in children.get(type, []):
                    result.setdefault(type, [])
                    result[type].append(self._browseTree(
                        user, subdoc['_id'], depth - 1,
                        limit=limit, offset=offset, sort=sort, fields=fields,
                        **kwargs))
        return result

    @autoDescribeRoute(
        Description('Get a list of users and collections, possibly recursing '
                    'into folders')
        .param('depth', 'The depth to recurse.', required=False, dataType='int', default=1)
        .pagingParams(defaultSort='lowerName')
        .jsonParam('fields', 'JSON list of additional fields to include',
                   required=False, requireArray=True)
        .errorResponse()
        .errorResponse('Access was denied for the resource.', 403)
    )
    @access.public
    def browseTreeRoot(self, **kwargs):
        user = self.getCurrentUser()
        return self._browseTree(user, **kwargs)

    @autoDescribeRoute(
        Description('Get a list of child folder and items.')
        .param('id', 'The ID of the resource.', paramType='path')
        .param('depth', 'The depth to recurse.', required=False, dataType='int', default=1)
        .pagingParams(defaultSort='lowerName')
        .jsonParam('fields', 'JSON list of additional fields to include',
                   required=False, requireArray=True)
        .errorResponse()
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the resource.', 403)
    )
    @access.public
    def browseTreeById(self, id, **kwargs):
        user = self.getCurrentUser()
        return self._browseTree(user, id, **kwargs)
