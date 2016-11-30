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
        if self.getTCGAType(cancer) != 'cancer':
            raise ValidationException(
                'A Case model must be a child of a cancer'
            )
        if not self.case_re.match(self.getTCGA(doc).get('label', '')):
            raise ValidationException(
                'Invalid label in TCGA metadata'
            )
        return doc

    def importDocument(self, doc, **kwargs):
        recurse = kwargs.get('recurse', False)
        self.setTCGA(doc, label=doc['name'])
        doc = super(Case, self).importDocument(doc, **kwargs)
        if not recurse:
            return doc

        childModel = self.model('slide', 'digital_slide_archive')
        children = self.model('folder').childFolders(
            doc, 'folder', user=kwargs.get('user')
        )
        for child in children:
            try:
                childModel.importDocument(child, **kwargs)
            except ValidationException:
                pass
        return doc
