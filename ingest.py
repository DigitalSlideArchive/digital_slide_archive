import datetime
import dateutil.parser
import girder_client
import lxml.html
import requests
import stampfile

# Root path for scraping SVS files
URLBASE = 'https://tcga-data.nci.nih.gov/tcgafiles/ftp_auth/distro_ftpusers/anonymous/tumor/lgg/bcr/nationwidechildrens.org/tissue_images/slide_images/nationwidechildrens.org_LGG.tissue_images.Level_1.112.3.0/'


def findSvsFiles(url):
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
            for svs in findSvsFiles(url + name):
                yield svs
        elif name.endswith('.svs'):  # svs file
            mtime = row.xpath('.//td[3]/text()')[0].strip()
            yield (url + name, mtime)


def extractMetadataFromUrl(url):
    """
    Given a full path to an SVS file, we extract all relevant metadata that is
    represented in the filename and its absolute path.
    """
    basename = url.split('/')[-1]

    # TODO implement metadata extraction
    return basename


def ingest(clientArgs, importUrl, parentType, parentId, login=None,
           password=None):
    stamps = stampfile.readStamps()
    client = girder_client.GirderClient(**clientArgs)
    #client.authenticate(login, password, interactive=(password is None))

    dateThreshold = stamps.get(importUrl)

    if dateThreshold:
        print('--- Limiting to files newer than %s.' % str(dateThreshold))

    maxDate = dateThreshold or datetime.datetime.min

    for url, mtime in findSvsFiles(importUrl):
        date = dateutil.parser.parse(mtime)
        maxDate = max(maxDate, date)

        if dateThreshold and date < dateThreshold:
            print('--- Skipping %s due to mtime.' % url)
            continue

        metadata = extractMetadataFromUrl(url)

    if maxDate:
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

    args = parser.parse_args()

    clientArgs = {
        'host': args.host,
        'port': int(args.port),
        'apiRoot': args.api_root,
        'scheme': args.scheme
    }

    ingest(clientArgs, URLBASE, args.parent_type, args.parent_id,
           login=args.username, password=args.password)
