# How to add a new endpoint:
# 1. Add the route in the __init__ method.  See
# http://girder.readthedocs.io/en/latest/plugin-development.html?highlight=route
#    for details.
# 2. Add a new method to the DSAEndpointsResource class.  If it has a
#    @describeRoute decorator, it will show up in the Swagger API.

from girder import logger
from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import Resource, RestException
from girder.constants import AccessType

from .system import allChildFolders, allChildItems


class DSAEndpointsResource(Resource):

    def __init__(self):
        super(DSAEndpointsResource, self).__init__()

        self.resourceName = 'dsa_endpoints'
        self.route('GET', ('child_metadata', ':id'), self.getChildMetadata)

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
