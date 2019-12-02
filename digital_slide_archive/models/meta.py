import mimetypes
import re

import six

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder.utility.model_importer import ModelImporter

from ..constants import TCGACollectionSettingKey


def pruneNoneValues(d):
    """Recursively prune dictionary items with value `None`."""
    toDelete = [k for k, v in six.viewitems(d) if v is None]
    for k in toDelete:
        del d[k]
    for _, v in six.viewitems(d):
        if isinstance(v, dict):
            pruneNoneValues(v)


def updateDict(d, u):
    """Recursively update a dictionary with items from another."""
    for k, v in six.viewitems(u):
        if isinstance(v, dict):
            r = updateDict(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


class TCGAModel(object):
    """
    This class is used as a mixin for all TCGA model classes.  TCGA models
    are distinguished by the existence of a `tcga` property at the top level
    of their document.  Each model can use this key differently, but all
    models must set `tcga.type` to be the model subclass.  This is handled
    automatically by the mixin from the TCGAType static call property.
    This mixin overrides several Girder core methods to properly set tcga
    metadata as well as limit queries to only the given model type.

    The special `tcga` object contained in these documents can contain an
    additional `meta` field which is interpreted as model specific metadata.
    This is analogous to the `meta` field in Girder core items and folders.
    """

    #: Additional indices to add to the collection
    TCGAIndices = []

    #: Matches valid case names
    case_re = re.compile(r'tcga-[a-z0-9]{2}-[a-z0-9]{4}', flags=re.I)

    #: Matches valid uuid's
    uuid_re = re.compile(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        flags=re.I
    )

    #: Matches valid tcga barcodes
    barcode_re = re.compile(
        case_re.pattern + r'[0-9a-z-]*',
        flags=re.I
    )

    #: Parses tcga slide image file names
    image_re = re.compile(
        r'^(?P<barcode>(?P<case>' +
        case_re.pattern + r')[0-9a-z-]*)\.' +
        r'(?P<uuid>' + uuid_re.pattern + r')\.svs$',
        flags=re.I
    )

    #: Parses tcga pathology report file names
    pathology_re = re.compile(
        r'^(?P<case>' + case_re.pattern +
        r')\.(?P<uuid>' + uuid_re.pattern +
        r')\.pdf$',
        flags=re.I
    )

    def initialize(self, **kwargs):
        """Expose the tcga key as public metadata."""
        self.exposeFields(AccessType.READ, fields='tcga')
        self.ensureIndices(['tcga.type'] + list(self.TCGAIndices))
        super(TCGAModel, self).initialize(**kwargs)
        self.name = self.TCGAType

    def save(self, doc, baseModel=False, **kwargs):
        """Set the TCGA model type on save."""
        if not baseModel:
            self.setTCGA(doc, type=self.TCGAType)
        return super(TCGAModel, self).save(doc, **kwargs)

    def find(self, query=None, **kwargs):
        """Append TCGA model type to any query on this model."""
        query = query or {}
        query['tcga.type'] = self.TCGAType
        return super(TCGAModel, self).find(query, **kwargs)

    def findOne(self, query=None, **kwargs):
        """Append TCGA model type to any query on this model."""
        query = query or {}
        query['tcga.type'] = self.TCGAType
        return super(TCGAModel, self).findOne(query, **kwargs)

    def setTCGA(self, doc, **tcga):
        """Update the TCGA object and prune values of None."""
        self.getTCGA(doc).update(tcga)
        pruneNoneValues(self.getTCGA(doc))
        return self

    def getTCGA(self, doc):
        """Return the TCGA object."""
        return doc.setdefault('tcga', {})

    def updateTCGAMeta(self, doc, meta):
        """Update TCGA metadata."""
        meta = updateDict(self.getTCGAMeta(doc), meta)
        pruneNoneValues(meta)
        return self

    def getTCGAMeta(self, doc):
        """Return TCGA metadata from a document."""
        tcga = self.getTCGA(doc)
        return tcga.setdefault('meta', {})

    def removeTCGA(self, doc):
        """Remove the tcga key and save the document.

        This method will effectively reset the document so that
        it no longer behaves as a TCGA document.  This is the
        opposite of the import methods that promote Girder models
        to TCGA types.
        """
        if 'tcga' in doc:
            del doc['tcga']
            self.save(doc, baseModel=True, validate=False)
        return doc

    def getTCGAType(self, doc):
        """Get the type of model expressed by the document."""
        return self.getTCGA(doc).get('type')

    def getTCGACollection(self):
        """Get the unique TCGA collection from the settings collection."""
        tcga = Setting().get(
            TCGACollectionSettingKey
        )
        if tcga is None:
            raise Exception(
                'TCGA collection id not initialized in settings'
            )
        return Collection().load(
            tcga, force=True
        )

    def __upper(self, obj, key):
        if key in obj:
            obj[key] = obj[key].upper()

    def __lower(self, obj, key):
        if key in obj:
            obj[key] = obj[key].lower()

    def _parse(self, name, regex):
        m = regex.match(name)
        if m is None:
            raise ValidationException('Invalid name')
        d = m.groupdict()
        self.__lower(d, 'uuid')
        self.__upper(d, 'barcode')
        self.__upper(d, 'case')
        return d

    def parseImage(self, name):
        """Parse a slide image file name."""
        return self._parse(name, self.image_re)

    def parsePathology(self, name):
        """Parse a pathology report file name."""
        return self._parse(name, self.pathology_re)

    @classmethod
    def setMimeType(cls, doc):
        """Set the mime type of a file document."""
        oldType = doc.get('mimeType')
        newType = mimetypes.guess_type(
            doc.get('name', '')
        )[0]
        doc['mimeType'] = newType
        return newType != oldType

    def importDocument(self, doc, **kwargs):
        """Promote a Girder core document to a TCGA model."""
        self.setTCGA(doc)
        self.save(doc)
        if doc.get('_modelType') == 'item':
            fileModel = File()
            files = Item().childFiles(doc)
            for file in files:
                if self.setMimeType(file):
                    fileModel.save(file)
        return doc

    def loadDocument(self, id, **kwargs):
        """Load a user, folder, item, or collection document."""
        for modelType in ('collection', 'user', 'folder', 'item'):
            model = ModelImporter.model(modelType)
            try:
                doc = model.load(id, **kwargs)
                if doc:
                    doc['_modelType'] = modelType
                    return doc
            except ValidationException:
                pass
        raise ValidationException(
            'Invalid document id provided'
        )

    def iterateItems(self, doc, **kwargs):
        """Iterate over all items under the given document."""
        folder = Folder()
        item = Item()
        for child in item.find({'folderId': doc['_id']}):
            yield child

        for child in folder.find({'parentId': doc['_id']}):
            for subchild in self.iterateItems(child, **kwargs):
                yield subchild

    def childFolders(self, parent, parentType, user=None, limit=0, offset=0,
                     sort=None, filters=None, cursor=False, **kwargs):
        """Add a ``cursor`` option to the standard childFolders method.

        The cursor option will ensure the response is a mongo cursor rather
        than a generic generator.  The resulting cursor will *not* be
        filtered by access control.  This option exists to allow efficient
        paging for resources that don't require fine grained permissions.
        """
        if not cursor:
            return super(TCGAModel, self).childFolders(
                parent, parentType, limit=limit, offset=offset, sort=sort, **kwargs)

        parentType = parentType.lower()
        q = {
            'parentId': parent['_id'],
            'parentCollection': parentType
        }
        q.update(filters or {})
        return self.find(q, sort=sort, limit=limit, offset=offset)
