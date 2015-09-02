import girder_client
import lxml.html
import requests

# Root path for scraping SVS files
URLBASE = 'https://tcga-data.nci.nih.gov/tcgafiles/ftp_auth/distro_ftpusers/anonymous/tumor/lgg/'


def findSvsFiles(url):
    """
    Given a URL to an apache mod_autoindex directory listing, recursively
    scrapes the listing for .svs files. This is a generator that yields each
    such file found in the listing.
    """
    xml = requests.get(url + '?F=0').text
    doc = lxml.html.fromstring(xml)

    children = doc.xpath('.//li/a/text()')

    for child in children:
        child = child.strip()
        if child.endswith('/'):  # subdirectory
            for svs in findSvsFiles(url + child):
                yield svs
        elif child.endswith('.svs'):  # svs file
            yield url + child


def extractMetadataFromUrl(url):
    basename = url.split('/')[-1]
    return basename


def ingest(clientArgs, parentType, parentId, login=None, password=None):
    client = girder_client.GirderClient(**clientArgs)
    #client.authenticate(login, password, interactive=(password is None))

    for url in findSvsFiles(URLBASE):
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
           password=args.password)
