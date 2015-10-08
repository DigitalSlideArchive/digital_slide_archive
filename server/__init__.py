from .rest import tcga


def load(info):
    info['apiRoot'].tcga = tcga.Tcga()
