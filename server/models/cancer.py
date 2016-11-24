from girder.models.folder import Folder
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Cancer(TCGAModel, Folder):

    TCGAType = 'cancer'

    def validate(self, doc, **kwargs):
        super(Cancer, self).validate(doc, **kwargs)
        if doc['parentCollection'] != 'collection':
            raise ValidationException(
                'A Cancer model must be a child of a collection'
            )
        return doc
