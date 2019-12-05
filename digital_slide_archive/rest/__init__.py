# -*- coding: utf-8 -*-

from . import tcga
from . import aperio
from . import system
from .image_browse_resource import ImageBrowseResource
from .dsa_resource import DigitalSlideArchiveResource


def addEndpoints(apiRoot):
    """
    This adds endpoints from each module.

    :param apiRoot: Girder api root class.
    """
    system.addSystemEndpoints(apiRoot)
    apiRoot.tcga = tcga.TCGAResource()
    aperio.addItemEndpoints(apiRoot.item)
    aperio.addTcgaEndpoints(apiRoot.tcga)

    ImageBrowseResource(apiRoot)

    apiRoot.digital_slide_archive = DigitalSlideArchiveResource()
