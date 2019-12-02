from girder.models.folder import Folder
from girder.models.model_base import ValidationException

from .case import Case
from .meta import TCGAModel


class Slide(TCGAModel, Folder):

    TCGAType = 'slide'

    def validate(self, doc, **kwargs):
        if not doc.get('parentCollection') == 'folder':
            raise ValidationException(
                'A Slide model must be a child of a folder'
            )
        super(Slide, self).validate(doc, **kwargs)
        case = Case().load(
            doc['parentId'], force=True)
        if not case or self.getTCGAType(case) != 'case':
            raise ValidationException(
                'A Slide model must be a child of a case'
            )
        return doc

    def importDocument(self, doc, **kwargs):
        from .image import Image

        recurse = kwargs.get('recurse', False)
        parent = Case().load(
            doc.get('parentId'), force=True
        )
        if not parent:
            raise ValidationException(
                'Invalid folder document'
            )
        tcga = self.getTCGA(parent)
        tcga.pop('meta', None)
        self.setTCGA(doc, **tcga)
        doc = super(Slide, self).importDocument(doc, **kwargs)
        if not recurse:
            return doc

        childModel = Image()
        children = Folder().childItems(
            doc, user=kwargs.get('user')
        )
        for child in children:
            try:
                childModel.importDocument(child, **kwargs)
            except ValidationException:
                pass
        return doc
