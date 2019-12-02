from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import boundHandler, loadmodel
from girder.constants import AccessType
from girder.models.item import Item

from ..models.aperio import Aperio


def addItemEndpoints(itemRoot):
    itemRoot.route('POST', (':id', 'aperio'), importDocument)
    itemRoot.route('GET', (':id', 'aperio'), findAperio)
    itemRoot.route('DELETE', (':id', 'aperio'), removeAperio)
    itemRoot.route('PUT', (':id', 'aperio'), modifyAperio)


def addTcgaEndpoints(tcgaRoot):
    tcgaRoot.route('POST', ('aperio',), importTCGADocument)


@describeRoute(
    Description('Import an item as an Aperio annotation')
    .param('id', 'The id of the item or root to import')
    .param('tag', 'Import annotations with this tag',
           required=False)
    .param('recursive', 'Perform a recursive search for annotations',
           required=False, dataType='boolean')
)
@access.admin
@loadmodel(model='item', level=AccessType.ADMIN)
@boundHandler()
def importTCGADocument(self, item, params):
    user = self.getCurrentUser()
    token = self.getCurrentToken()
    recursive = params.get('recursive')
    tag = params.get('tag')
    aperio = Aperio()
    return aperio.importTCGADocument(
        item, tag=tag,
        user=user, token=token,
        recurse=recursive
    )


@describeRoute(
    Description('Import an item as an Aperio annotation')
    .param('id', 'The ID of the item containing the annotation file',
           paramType='path')
    .param('imageId', 'The ID of the slide image', required=True)
    .param('tag', 'A searchable tag to store with the metadata',
           required=False)
)
@access.admin
@loadmodel(model='item', level=AccessType.ADMIN)
@boundHandler()
def importDocument(self, item, params):
    self.requireParams('imageId', params)
    user = self.getCurrentUser()
    token = self.getCurrentToken()
    tag = params.get('tag')
    imageId = params['imageId']
    image = Item().load(
        imageId,
        user=user, level=AccessType.READ, exc=True
    )
    aperio = Aperio()
    return aperio.importDocument(
        item, image, tag=tag,
        user=user, token=token
    )


@describeRoute(
    Description('Find Aperio annotation items associated with a slide image.')
    .param('id', 'The ID of the slide image item', paramType='path')
    .param('tag', 'Filter by the given tag string', required=False)
    .pagingParams(defaultSort='name')
)
@access.public
@loadmodel(model='item', level=AccessType.READ)
@boundHandler()
def findAperio(self, item, params):
    limit, offset, sort = self.getPagingParameters(params, 'name')
    user = self.getCurrentUser()
    tag = params.get('tag')
    aperio = Aperio()
    docs = list(aperio.findAperio(
        item, tag=tag,
        user=user, level=AccessType.READ
    ))

    for doc in docs:
        files = aperio.childFiles(doc, limit=1)
        if files.count():
            doc['file'] = files[0]

    return docs


@describeRoute(
    Description('Remove Aperio specific metadata from an item')
    .param('id', 'The ID of the annotation item', paramType='path')
)
@access.admin
@loadmodel(model='item', level=AccessType.WRITE)
@boundHandler()
def removeAperio(self, item, params):
    return Aperio().removeAperio(
        item
    )


@describeRoute(
    Description('Set the tag associated with the annotation file')
    .param('id', 'The ID of the annotation file', paramType='path')
    .param('tag', 'A searchable tag to store with the metadata')
)
@access.admin
@loadmodel(model='item', level=AccessType.WRITE)
@boundHandler()
def modifyAperio(self, item, params):
    return Aperio().setTag(
        item, tag=params.get('tag')
    )
