from girder.models.folder import Folder
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Case(TCGAModel, Folder):

    TCGAType = 'case'
    TCGAIndices = [
        'tcga.label'
    ]

    def validate(self, doc, **kwargs):
        if doc.get('parentCollection') != 'folder':
            raise ValidationException(
                'A Case model must be a child of a folder'
            )
        super(Case, self).validate(doc, **kwargs)
        cohort = self.model('cohort', 'digital_slide_archive').load(
            doc['parentId'], force=True)
        if not cohort or self.getTCGAType(cohort) != 'cohort':
            raise ValidationException(
                'A Case model must be a child of a cohort'
            )
        if not self.case_re.match(self.getTCGA(doc).get('label', '')):
            raise ValidationException(
                'Invalid label in TCGA metadata'
            )
        return doc

    def importDocument(self, doc, **kwargs):
        recurse = kwargs.get('recurse', False)
        parent = self.model('cohort', 'digital_slide_archive').load(
            doc.get('parentId'), force=True
        )
        if not parent:
            raise ValidationException(
                'Invalid folder document'
            )
        tcga = self.getTCGA(parent)
        tcga['label'] = doc['name']
        self.setTCGA(doc, **tcga)
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
