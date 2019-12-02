import re

from girder.constants import AccessType
from girder.models.file import File
from girder.models.item import Item
from girder.models.model_base import ValidationException

from .image import Image as TCGAImage
from .meta import TCGAModel


class Aperio(Item):

    #: Parses tcga Aperio annotation file names as tcga types
    aperio_re = re.compile(
        r'^(?P<barcode>(?P<case>' +
        TCGAModel.case_re.pattern + r')[0-9a-z-]*)\.xml',
        flags=re.I
    )

    def initialize(self, **kwargs):
        """Expose aperio key as public metadata."""
        self.exposeFields(AccessType.READ, fields='aperio')
        self.ensureIndices(['aperio.image', 'aperio.tag'])
        return super(Aperio, self).initialize(**kwargs)

    def validate(self, doc, **kwargs):
        """Ensure the item has valid metadata."""
        super(Aperio, self).validate(doc, **kwargs)
        meta = doc.setdefault('aperio', {})
        imageId = meta.get('image')
        try:
            Item().load(imageId, force=True)
        except Exception:
            raise ValidationException(
                'The item is not associated with a valid image.'
            )

        files = Item().childFiles(doc)
        if files.count() != 1:
            raise ValidationException(
                'The annotation item must have exactly one file.'
            )

        meta.setdefault('tag', None)
        return doc

    def setTag(self, doc, tag):
        meta = doc.setdefault('aperio', {})
        meta['tag'] = tag
        self.save(doc)
        return doc

    def importDocument(self, doc, image, **kwargs):
        """Promote the item document to an aperio type."""
        tag = kwargs.get('tag')
        meta = doc.setdefault('aperio', {})
        meta['image'] = image['_id']
        self.setTag(doc, tag)
        fileModel = File()
        files = Item().childFiles(doc)
        for file in files:
            if TCGAModel.setMimeType(file):
                fileModel.save(file)
        return doc

    def importTCGADocument(self, doc, **kwargs):
        """Import the annotation item into a tcga structure."""
        recurse = kwargs.get('recurse', False)

        if doc.get('_modelType', 'item') == 'item':
            name = doc['name']
            d = self.aperio_re.match(name).groupdict()
            image = TCGAImage().findOne({
                'tcga.barcode': d['barcode'].upper()
            })
            self.importDocument(doc, image, **kwargs)

            return doc
        elif recurse:
            for item in self.iterateItems(doc):
                try:
                    self.importTCGADocument(item, **kwargs)
                except ValidationException:
                    pass
        else:
            raise ValidationException('Invalid model type')

    def findAperio(self, image, tag=None, **kwargs):
        """Find Aperio annotations associated with the given image."""
        query = {
            'aperio.image': image['_id'],
        }
        if tag is not None:
            query['aperio.tag'] = tag
        return self.find(query, **kwargs)

    def removeAperio(self, doc):
        """Remove Aperio metadata from an item."""
        if 'aperio' in doc:
            del doc['aperio']
            Item().save(doc)
        return doc
