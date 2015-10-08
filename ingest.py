import data_transfer
import datetime
import dateutil.parser
import girder_client
import lxml.html
import requests
import stampfile

from server.utils import extractMetadataFromUrl

# Root path for scraping SVS files
URLBASE = 'https://tcga-data.nci.nih.gov/tcgafiles/ftp_auth/distro_ftpusers/anonymous/tumor/lgg/bcr/nationwidechildrens.org/tissue_images/'


def findSvsFilesAutoIndex(url):
    """
    Given a URL to an apache mod_autoindex directory listing, recursively
    scrapes the listing for .svs files. This is a generator that yields each
    such file found in the listing as a tuple whose first element is the URL
    and whose second element is its modified time as reported by the server.
    """
    doc = lxml.html.fromstring(requests.get(url + '?F=2').text)
    rows = doc.xpath('.//table//tr')

    for row in rows:
        name = row.xpath('.//td[2]/a/text()')

        if not name:  # F=2 gives us some header rows that only contain <th>
            continue

        name = name[0].strip()

        if name.endswith('/'):  # subdirectory
            for svs in findSvsFilesAutoIndex(url + name):
                yield svs
        elif name.endswith('.svs'):  # svs file
            mtime = row.xpath('.//td[3]/text()')[0].strip()
            yield (url + name, mtime)


def ingest(client, importUrl, parent, parentType, verbose=False):
    stamps = stampfile.readStamps()
    dateThreshold = stamps.get(importUrl)

    if dateThreshold:
        print('--- Limiting to files newer than %s.' % str(dateThreshold))

    maxDate = dateThreshold or datetime.datetime.min

    for url, mtime in findSvsFiles(importUrl):
        date = dateutil.parser.parse(mtime)
        maxDate = max(maxDate, date)

        if dateThreshold and date <= dateThreshold:
            if verbose:
                print('--- Skipping %s due to mtime.' % url)
            continue

        info = extractMetadataFromUrl(url)
        info['itemMetadata']['MTime'] = mtime
        data_transfer.createGirderData(client, parent, parentType, info, url)

    stamps[importUrl] = maxDate
    stampfile.writeStamps(stamps)


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
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    client = girder_client.GirderClient(
        host=args.host, port=int(args.port), apiRoot=args.api_root, scheme=args.scheme)
    client.authenticate(args.username, args.password, interactive=(args.password is None))

    parent = client.getResource(args.parent_type, args.parent_id)

    ingest(client, URLBASE, parent, args.parent_type, verbose=args.verbose)
