from girder.models.folder import Folder
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Case(TCGAModel, Folder):

    TCGAType = 'case'

    def validate(self, doc, **kwargs):
        super(Case, self).validate(doc, **kwargs)
        if not doc['parentCollection'] == 'collection':
            raise ValidationException(
                'A Case model must be a child of a collection'
            )
        return doc
