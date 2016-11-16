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
        if not slide.get('tcgaType') == 'case':
            raise ValidationException(
                'An image must be a child of a Slide'
            )
