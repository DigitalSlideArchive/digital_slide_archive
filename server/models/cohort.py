from girder.models.folder import Folder
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Cohort(TCGAModel, Folder):

    TCGAType = 'cohort'

    def validate(self, doc, **kwargs):
        super(Cohort, self).validate(doc, **kwargs)
        if doc['parentCollection'] != 'collection':
            raise ValidationException(
                'A Cohort model must be a child of a collection'
            )
        return doc

    def importDocument(self, doc, **kwargs):
        recurse = kwargs.get('recurse', False)
        self.setTCGA(doc, cohort=doc['name'])
        doc = super(Cohort, self).importDocument(
            doc, **kwargs)
        if not recurse:
            return doc

        childModel = self.model('case', 'digital_slide_archive')
        children = self.model('folder').childFolders(
            doc, 'folder', user=kwargs.get('user')
        )
        for child in children:
            try:
                childModel.importDocument(child, **kwargs)
            except ValidationException:
                pass
        return doc
