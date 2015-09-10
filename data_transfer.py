import requests


def formatSize(size):
    prefixes = ['', 'K', 'M', 'G', 'T']
    i = 0
    while size > 1024 and i < len(prefixes) - 1:
        size /= 1024.0
        i += 1
    return '%.1f %sB' % (size, prefixes[i])


def _uploadProgress(info):
    print('%s / %s' % (formatSize(info['current']), formatSize(info['total'])))


def createGirderData(client, parent, parentType, info, url):
    folder = client.load_or_create_folder(
        info['folderName'], parent['_id'], parentType)

    item = client.load_or_create_item(info['itemName'], folder['_id'])

    client.addMetadataToItem(item['_id'], info['itemMetadata'])

    files = [f['name'] for f in client.get('item/%s/files' % item['_id'])]
    if info['basename'] not in files:
        # Make HEAD request to get size
        hr = requests.head(url)
        size = int(hr.headers['Content-Length'])

        print('Transferring %s (size=%s)' % (url, formatSize(size)))

        resp = requests.get(url, stream=True)
        client.uploadFile(item['_id'], resp.raw, info['basename'], size,
                          progressCallback=_uploadProgress)
    else:
        print('Skipping %s, file already exists.' % url)
