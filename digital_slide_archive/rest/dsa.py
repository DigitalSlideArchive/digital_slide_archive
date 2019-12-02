# How to add a new endpoint:
# 1. Add the route in the __init__ method.
# 2. Add a new method to the DSAEndpointsResource class.  If it has a
#    @describeRoute decorator, it will show up in the Swagger API.
#
# Girder's documentation is at http://girder.readthedocs.io.  It provides
# a broad range of documentation from the user, developer, and administrator
# perspectives.  A particularly relevant portion describes plugin
# development:
#   http://girder.readthedocs.io/en/latest/plugin-development.html
#
# There are a number of plugins written for girder that may be helpful
# examples when learning common tricks to modify the behavior.
#   https://github.com/girder/girder/tree/master/plugins
#
# It may also be useful to look at how girder defines it's own api resources.
# For example, https://github.com/girder/girder/blob/master/girder/api/v1/item.py

# The imports here are typically well documented in the code.  Readthedocs
# compiles all of the docstrings together into one place:
#   http://girder.readthedocs.io/en/latest/api-docs.html
from girder import logger
from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import Resource, RestException
from girder.constants import AccessType
from girder.models.item import Item
from girder.utility.model_importer import ModelImporter

from .system import allChildFolders, allChildItems


# The `DSAEndpointsResource` class derived from `Resource` defines
# a group of endpoints that are attached to girder's api object
# in `__init__.py`.
class DSAEndpointsResource(Resource):

    def __init__(self):
        super(DSAEndpointsResource, self).__init__()

        # This defines the top level path of the new endpoints.  In this case,
        # new endpoints will be added at `/api/v1/dsa_endpoints/...`
        self.resourceName = 'dsa_endpoints'

        # The route function tells girder to route calls to the endpoint to
        # a specific function.  The arguments here mean:

        #  1st: This is for GET requests
        #  2nd: This describes the path of the endpoint.
        #  3rd: The function that will be called.
        #
        # The `:id` component in the path is a wildcard that matches any string
        # The value matched will be passed as an argument to the function.  As
        # an example if you make a GET request to
        #   `/api/v1/dsa_endpoints/child_metadata/foobar`
        # the function `self.getChildMetadata` will be called with the parameter
        # `id="foobar"`.
        self.route('GET', ('child_metadata', ':id'), self.getChildMetadata)

        # Similarly, this route handles calls to:
        #  `GET /api/v1/dsa_endpoints/query_metadata`
        self.route('GET', ('query_metadata',), self.findItemsByMetadata)

    # The `autoDescrbeRoute` (and `describeRoute` used in older code)
    # serves to generate the swagger documentation that looks like:
    #   https://data.kitware.com/api/v1
    #
    # The api for this is described at https://goo.gl/hnU3ws.
    @autoDescribeRoute(
        # Instantiate the instance with a basic description of the endpoint.
        Description('Get all metadata for a resource and all folders and '
                    'items that are children of a resource.')
        # Add a required "path" parameter (this is the `:id` component in the
        # route).
        .param('id', 'The ID of the resource.', paramType='path')
        # Add a required "query" parameter... e.g. `?type=collection`.
        .param('type', 'The type of the resource', enum=['folder', 'collection', 'user'])
        # The following to lines document common rest errors that can occur
        # when calling this endpoint.  This is for documentation only.
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the resource.', 403)
    )
    # This makes the endpoint accessible without logging in.  Related decorators
    # are described in https://goo.gl/LMZA5V
    @access.public
    def getChildMetadata(self, id, params):
        # The `autoDescribeRoute` decorator processes the incoming request and populates
        # the function arguments.  Path parameters are added as individual arguments,
        # while query parameters are packed into the `params` dictionary.

        user = self.getCurrentUser()
        modelType = params['type']
        model = ModelImporter.model(modelType)
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

        # By default, responses to girder endpoints are json encoded when returned to
        # the client.  In this case, it is a dictionary mapping `id` -> `metadata`.
        return results

    # This endpoint returns a paginated list of all items with a given (key, value)
    # pair in their metadata.  This endpoint can be called as follows:
    #
    # /dsa_endpoints/query_metadata?key=doctor&value="John Doe"&limit=10&sort=created&sortdir=-1
    #
    # This will return a list of items matched as `{'meta': {'doctor': 'John Doe'}}`.
    # It will return at most 10 items starting from the most recently created.
    @autoDescribeRoute(
        Description('Get a list of items with a specific metadata value.')
        # This is a required string parameter representing the key in the metadata.
        .param('key', 'The metadata key')
        # This is the value which should be json encoded.
        .jsonParam('value', 'The (json encoded) metadata value')
        # This adds paging parameters "limit", "offset", and "sort".  By default
        # it sorts by the `name` field of the item in ascending order.
        .pagingParams('name')
        # The following to lines document common rest errors that can occur
        # when calling this endpoint.  This is for documentation only.
        .errorResponse('Required parameters were not provided.')
        .errorResponse('Invalid value provided.')
    )
    # This makes the endpoint accessible without logging in.  Related decorators
    # are described in https://goo.gl/LMZA5V
    @access.public
    def findItemsByMetadata(self, key, value, limit, offset, sort):
        # Construct a mongo query from the parameters given.  Developers should
        # be careful when constructing these queries to ensure that private information
        # is not leaked.  In this example, the user could pass an arbitrary dictionary
        # which could involve an aggregation pipeline, so we check that only simple types
        # are accepted.
        if isinstance(value, (list, dict)):
            # This is a special type of exception that tells girder to respond with
            # an HTTP response with the given code and message.  See https://goo.gl/SpHqxE
            raise RestException('The value must not be a dictionary or list.', code=400)

        query = {
            'meta': {
                key: value
            }
        }

        # This gets the logged in user who created the request.  If it is an anonymous
        # request, this value will be `None`.
        user = self.getCurrentUser()

        # Here, item is a "model" class which is a single instance providing an api
        # that wraps traditional mongo queries.  This API is described at:
        # http://girder.readthedocs.io/en/latest/api-docs.html?#models
        item = Item()

        # This runs a "find" operation on the item collection returning a mongo cursor.
        cursor = item.find(query, sort=sort)

        # The `filterResultsByPermission` allows paged access to a mongo query while
        # filtering out documents that the current user doesn't have access to.  In
        # this case, it requires the current user have read access to the items.  The
        # return value is an iterator that begins at `offset` and ends at `offset + limit`.
        response = item.filterResultsByPermission(
            cursor,
            user=user, level=AccessType.READ,
            limit=limit, offset=offset
        )

        # Finally, we turn the iterator into an explicit list for return to the user.
        # Girder handles json encoding the response.
        return list(response)
