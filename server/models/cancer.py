from girder.models.folder import Folder
from girder.models.model_base import ValidationException

from .meta import TCGAModel


class Cancer(TCGAModel, Folder):

    TCGAType = 'cancer'
