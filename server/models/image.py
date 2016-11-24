from girder.models.item import Item
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Image(TCGAModel, Item):

    TCGAType = 'image'

    def validate(self, doc, **kwargs):
        super(Image, self).validate(doc, **kwargs)
        if 'largeImage' not in doc:
            raise ValidationException(
                'An image item must be a "large_image"'
            )
        slide = self.model('slide', 'digital_slide_archive').load(
            doc['folderId'], force=True)
        if not self.getTCGAType(slide) == 'slide':
            raise ValidationException(
                'An image must be a child of a slide'
            )
        tcga = self.getTCGA()
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

    def importDocument(self, doc):
        """Import a slide item into a `case` folder."""
        name = doc['name']
        tcga = self.parseImage(name)
        self.setTCGA(doc, **tcga)
        return super(Image, self).importDocument(doc)
