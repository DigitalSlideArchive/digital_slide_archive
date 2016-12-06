from girder.models.item import Item

from .meta import TCGAModel


class Aperio(TCGAModel, Item):

    TCGAType = 'aperio'

    def importDocument(self, doc, **kwargs):
        name = doc['name']
        tcga = self.parseAperio(name)
        self.setTCGA(doc, **tcga)

        return super(Aperio, self).importDocument(doc, **kwargs)
