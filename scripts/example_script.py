import girder_client
from girder_client import HttpError
import json


def print_http_error(err):
    print ('Request Error:\nstatus:%s\nresponse%s\nurl:%s'
           '\nmethod:%s ' % (err.status, err.responseText, err.url, err.method))


def recurse_get_resource(client, parent_folder, resource_type,
                         resource_list, parent_is_collection=False):
    # now get all folders
    folders = None
    folder_id_list = None
    if parent_is_collection:
        try:
            folders = client.listFolder(parent_folder,
                                        parentFolderType='collection')
        except HttpError as err:
            print_http_error(err)
            exit()
        folder_id_list = get_field(folders, '_id')
        if resource_type is 'folder':
            resource_list.extend(folders)

    else:

        try:
            folders = client.listFolder(parent_folder)
        except HttpError as err:
            print_http_error(err)
            return
        folder_id_list = get_field(folders, '_id')

        if resource_type is 'item':
            try:
                data = client.listItem(parent_folder)

                resource_list.extend(data)
            except HttpError as err:
                print_http_error(err)
                exit()
        elif resource_type is 'folder':
            resource_list.extend(folders)
        else:
            return
    for folder_id in folder_id_list:
        recurse_get_resource(client, folder_id, resource_type, resource_list)


def print_field(data, str_key):
    for i in range(len(data)):
        print(data[i][str_key])


def get_field(data, str_key):
    return [i[str_key] for i in data]


def turn_into_a_large_image(girder_client, file_id):
    # first check if the file is already a large image
    item_data = None
    try:
        item_data = gc.getItem(file_id)
    except HttpError as err:
        print_http_error(err)
        print('bad item id ')
    # if the item is already a large image return

    if 'largeImage' in item_data:
        return
    try:
        girder_client.post('item/%s/tiles' % file_id)
    except HttpError as err:
        print_http_error(err)


def isEmpty(girder_client, folder):
    item_list = []
    recurse_get_resource(girder_client, folder, 'item', item_list)
    if len(item_list) == 0:
        return True
    else:
        return False
girder_location = 'http://localhost:8080/api/v1'

collection_name = 'DG TCGA'
collection_id = None
request_url = 'resource/lookup?path=collection/%s' % (collection_name)
collection_data = None

new_folder_name = 'GBM'
new_folder_desc = 'orginizing patient data'
new_folder_id = None

img_type = '.jpeg'

# login to girder, you will be prompted for credentials
gc = girder_client.GirderClient(apiUrl=girder_location)
gc.authenticate(interactive=True)

# get the id of the desired collection
try:
    collection_data = gc.getResource(request_url)
except HttpError as err:
    print_http_error(err)
    exit()

collection_id = collection_data['_id']
new_folder_data = None
# create a folder under this collection or load a preexisting folder that exists
# with the same name and parent
try:
    new_folder_data = gc.load_or_create_folder(new_folder_name,
                                               collection_id, 'collection')
except HttpError as err:
    print_http_error(err)
    exit()
new_folder_id = new_folder_data['_id']

# get all folders in the collection
collection_composition = None
try:
    collection_composition = gc.listFolder(collection_id, 'collection')
except HttpError as err:
    print_http_error(err)
    print ('exited')
    exit()

# get the ids of all folders under the collection
collection_folders = get_field(collection_composition, '_id')
item_list = []
# create a list to store id of all svs items
img_list = []
# get a list of all items within each folder of the collection
recurse_get_resource(gc, collection_id, 'item', item_list,
                     parent_is_collection=True)

temp_img_id = None
print('Listing all %s items in the collection %s' % (img_type, collection_name))
for item in item_list:
    if img_type in item['name']:
        temp_img_id = item['_id']
        print('image name %s ' % (item['name']))
        img_list.append(temp_img_id)
        turn_into_a_large_image(gc, temp_img_id)

# now create PATIENT folders inside our new folder

patient_folder_list = []
patient_folder_name = 'Patient%d'

for i in range(1, 4):
    temp_name = patient_folder_name % (i)
    try:
        patient_folder_list.append(gc.load_or_create_folder(temp_name,
                                                            new_folder_id,
                                                            'folder'))
    except HttpError as err:
        print_http_error(err)
        print ('exited')
        exit()

# now lets move an image into the PATIENT1 folder

patient1_folder = patient_folder_list[0]
patient1_folder_id = patient1_folder['_id']

src_img_id = img_list[0]

move_params = {
    'resources': json.dumps({
        'item': [str(src_img_id)]}),
    'parentType': 'folder',
    'parentId': patient1_folder_id
}

try:
    gc.put('resource/move', move_params)
except HttpError as err:
    print_http_error(err)
    print ('exited')
    exit()

# now lets edit the PATIENT1 folder

patient1_meta_data = {'PatientAge': 22, 'PatientDeceased': True}

try:
    gc.addMetadataToFolder(patient1_folder_id, patient1_meta_data)
except HttpError as err:
    print_http_error(err)
    print ('exited')
    exit()

# lets add meta data to the image we moved
# note how the id remains the same
new_src_img_meta_data = {'SlideSource': 'FromTCGA', 'SlideType': 'DX'}
try:
    gc.addMetadataToItem(src_img_id, new_src_img_meta_data)
except HttpError as err:
    print_http_error(err)
    print ('exited')
    exit()

# find all folders determine if whether each folder is empty or not
all_folders = []

recurse_get_resource(gc, collection_id, 'folder',
                     all_folders, parent_is_collection=True)

# if the folder size is zero then delete it
for folder in all_folders:

    if 'size' in folder and isEmpty(gc, folder['_id']):
        try:
            print('will delete folder %s' % folder['name'])

            gc.delete('folder/%s' % folder['_id'])

        except HttpError as err:
            print_http_error(err)
            print('could not delete folder %s' % (folder['name']))
            print ('exited')
            exit()
# already have a list of all items under the designated collection
# check whether a file under an item is a README.txt
# if so delete the entire item
for item in item_list:
    temp_files = gc.listFile(item['_id'])
    for girder_file in temp_files:
        if 'README.txt' in girder_file['name']:
            print('deleting item %s' % item['name'])
            try:
                gc.delete('item/%s' % item['_id'])
            except HttpError as err:
                print_http_error(err)
                print('could not delete item %s' % (item['name']))
                print ('exited')
                exit()
