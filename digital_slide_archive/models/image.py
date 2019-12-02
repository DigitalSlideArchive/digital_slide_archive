from girder.models.file import File
from girder.models.item import Item
from girder.models.model_base import ValidationException
from girder_large_image.models.image_item import ImageItem

from .meta import TCGAModel
from .slide import Slide


class Image(TCGAModel, Item):

    TCGAType = 'image'

    def validate(self, doc, **kwargs):
        super(Image, self).validate(doc, **kwargs)
        if 'largeImage' not in doc:
            raise ValidationException(
                'An image item must be a "large_image"'
            )
        slide = Slide().load(
            doc['folderId'], force=True)
        if not slide or self.getTCGAType(slide) != 'slide':
            raise ValidationException(
                'An image must be a child of a slide'
            )
        tcga = self.getTCGA(doc)
        if not self.case_re.match(tcga.get('case', '')):
            raise ValidationException(
                'Invalid case name in TCGA metadata'
            )
        if not self.barcode_re.match(tcga.get('barcode', '')):
            raise ValidationException(
                'Invalid barcode in TCGA metadata'
            )
        if not self.uuid_re.match(tcga.get('uuid', '')):
            raise ValidationException(
                'Invalid uuid in TCGA metadata'
            )

        return doc

    def _setLargeImage(self, doc, fileId, user, token):
        if doc.get('largeImage', {}).get('fileId') == fileId:
            return
        file = File().load(fileId, user=user)
        try:
            return ImageItem.createImageItem(
                doc, file,
                user=user, token=token, createJob=False
            )
        except Exception:
            raise ValidationException(
                'Could not generate a large_image item'
            )

    def _findImageFile(self, doc):
        for file in self.childFiles(doc):
            if self.image_re.match(file['name']):
                return file['_id']

    def importDocument(self, doc, **kwargs):
        """Import a slide item into a `case` folder."""
        user = kwargs.get('user')
        token = kwargs.get('token')
        fileId = self._findImageFile(doc)
        if fileId is None:
            raise ValidationException(
                'Could not find a TCGA slide in item'
            )
        self._setLargeImage(doc, fileId, user, token)

        name = doc['name']
        parent = Slide().load(
            doc.get('folderId'), force=True
        )
        if not parent:
            raise ValidationException(
                'Invalid item document'
            )
        tcga = self.getTCGA(parent)
        tcga.update(self.parseImage(name))
        self.setTCGA(doc, **tcga)
        return super(Image, self).importDocument(doc, **kwargs)
