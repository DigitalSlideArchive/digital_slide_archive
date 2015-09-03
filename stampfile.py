import dateutil.parser
import os


_defaultPath = os.path.join(os.path.dirname(__file__), 'ingest_stamps.txt')


def readStamps(path=None):
    stamps = {}
    path = path or _defaultPath

    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                url, time = line.split(' ', 1)
                stamps[url] = dateutil.parser.parse(time)

    return stamps


def writeStamps(stamps, path=None):
    path = path or _defaultPath

    with open(path, 'w') as f:
        for url, time in stamps.items():
            f.write('%s %s\n' % (url, str(time)))
