from girder.models.item import Item
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Pathology(TCGAModel, Item):

    TCGAType = 'pathology'

    def validate(self, doc, **kwargs):
        super(Pathology, self).validate(doc, **kwargs)
        case = self.model('case', 'digital_slide_archive').load(
            doc['folderId'], force=True)
        if not self.getTCGAType(case) == 'case':
            raise ValidationException(
                'An pathology must be a child of a case'
            )
        return doc

    def importPathology(self, doc, user=None):
        """Import a pathology item into a `case` folder."""
        name = doc['name']
        tcga = self.parsePathology(name)
        self.setTCGA(doc, **tcga)

        case = self.model('case', 'digital_slide_archive').createFolder(
            parent=self.getTCGACollection(),
            name=tcga['case'], parentType='collection',
            creator=user, reuseExisting=True
        )

        self.move(doc, case)
        return doc
