from girder.constants import AccessType


class TCGAModel(object):

    def initialize(self, **kwargs):
        self.exposeFields(AccessType.READ, fields='tcgaType')
        super(TCGAModel, self).initialize(**kwargs)

    def save(self, doc, **kwargs):
        doc['tcgaType'] = self.TCGAType
        return super(TCGAModel, self).save(doc, **kwargs)

    def find(self, query=None, **kwargs):
        query = query or {}
        query['tcgaType'] = self.TCGAType
        return super(TCGAModel, self).find(query, **kwargs)

    def findOne(self, query=None, **kwargs):
        query = query or {}
        query['tcgaType'] = self.TCGAType
        return super(TCGAModel, self).findOne(query, **kwargs)
