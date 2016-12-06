from girder.models.item import Item
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Pathology(TCGAModel, Item):

    TCGAType = 'pathology'

    def importDocument(self, doc, **kwargs):
        """Import a pathology item into a `case` folder."""
        name = doc['name']
        tcga = self.parsePathology(name)
        self.setTCGA(doc, **tcga)

        return super(Pathology, self).importDocument(doc, **kwargs)
