from girder.models.folder import Folder
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Case(TCGAModel, Folder):

    TCGAType = 'case'

    def validate(self, doc, **kwargs):
        super(Case, self).validate(doc, **kwargs)
        if not doc['parentCollection'] == 'folder':
            raise ValidationException(
                'A Case model must be a child of a folder'
            )
        cancer = self.model('cancer', 'digital_slide_archive').load(
            doc['parentId'], force=True)
        if not self.getTCGAType(case) == 'cancer':
            raise ValidationException(
                'A Case model must be a child of a cancer'
            )
        if not self.case_re.match(self.getTCGA().get('label', '')):
            raise ValidationException(
                'Invalid label in TCGA metadata'
            )
        return doc

    def importDocument(self, doc):
        self.setTCGA(doc, label=doc['name'])
        return super(Case, self).importDocument(doc)
