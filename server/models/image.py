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
        return doc

    def importImage(self, doc, user=None):
        """Import a slide item into a `case` folder."""
        name = doc['name']
        tcga = self.parseImage(name)
        self.setTCGA(doc, **tcga)

        case = self.model('case', 'digital_slide_archive').createFolder(
            parent=self.getTCGACollection(),
            name=tcga['case'], parentType='collection',
            creator=user, reuseExisting=True
        )

        slide = self.model('slide', 'digital_slide_archive').createFolder(
            parent=case,
            name=tcga['barcode'], parentType='folder',
            creator=user, reuseExisting=True
        )

        self.move(doc, slide)
        return doc
