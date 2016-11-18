from girder.models.folder import Folder
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Slide(TCGAModel, Folder):

    TCGAType = 'slide'

    def validate(self, doc, **kwargs):
        super(Slide, self).validate(doc, **kwargs)
        if not doc['parentCollection'] == 'folder':
            raise ValidationException(
                'A Slide model must be a child of a folder'
            )
        case = self.model('case', 'digital_slide_archive').load(
            doc['parentId'], force=True)
        if not self.getTCGAType(case) == 'case':
            raise ValidationException(
                'A Slide model must be a child of a case'
            )
        return doc

    def getImage(self, doc):
        return self.model('image', 'digital_slide_archive').findOne(
            {'folderId': doc['_id']})
