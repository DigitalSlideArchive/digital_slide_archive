import datetime
import dateutil.parser
import girder_client
import lxml.html
import requests

# Root path for scraping SVS files
URLBASE = 'https://tcga-data.nci.nih.gov/tcgafiles/ftp_auth/distro_ftpusers/anonymous/tumor/lgg/'
# Dummy date threshold for testing
THRESHOLD = datetime.datetime.utcnow().replace(tzinfo=dateutil.tz.tzutc())


def findSvsFiles(url):
    """
    Given a URL to an apache mod_autoindex directory listing, recursively
    scrapes the listing for .svs files. This is a generator that yields each
    such file found in the listing.
    """
    doc = lxml.html.fromstring(requests.get(url + '?F=0').text)
    children = doc.xpath('.//li/a/text()')

    for child in children:
        child = child.strip()
        if child.endswith('/'):  # subdirectory
            for svs in findSvsFiles(url + child):
                yield svs
        elif child.endswith('.svs'):  # svs file
            yield url + child


def extractMetadataFromUrl(url):
    """
    Given a full path to an SVS file, we extract all relevant metadata that is
    represented in the filename and its absolute path.
    """
    basename = url.split('/')[-1]

    # TODO implement metadata extraction
    return basename


def isNewer(req, dateThreshold):
    """
    Use a HEAD request to the URL to try and detect whether the given resource
    has been modified since the given date threshold.
    """
    mtime = req.headers.get('Last-Modified')

    if mtime is None:
        return True

    return dateutil.parser.parse(mtime) >= dateThreshold


def ingest(clientArgs, parentType, parentId, login=None, password=None,
           dateThreshold=None):
    client = girder_client.GirderClient(**clientArgs)
    #client.authenticate(login, password, interactive=(password is None))

    for url in findSvsFiles(URLBASE):
        req = requests.head(url)

        if dateThreshold and not isNewer(req, dateThreshold):
            print 'Skipping %s due to mtime.' % url
            continue

        metadata = extractMetadataFromUrl(url)
        print metadata


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Import TCGA data into a girder server.')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', default='8080')
    parser.add_argument('--username')
    parser.add_argument('--password')
    parser.add_argument('--scheme')
    parser.add_argument('--api-root')
    parser.add_argument('--parent-type', default='collection',
                        help='(default: collection)')
    parser.add_argument('--parent-id', required=True)

    args = parser.parse_args()

    clientArgs = {
        'host': args.host,
        'port': int(args.port),
        'apiRoot': args.api_root,
        'scheme': args.scheme
    }

    ingest(clientArgs, args.parent_type, args.parent_id, login=args.username,
           password=args.password, dateThreshold=THRESHOLD)
