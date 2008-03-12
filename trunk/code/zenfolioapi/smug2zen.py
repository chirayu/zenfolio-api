""" This file transfers a gallery from smugmug to zenfolio. It make a
gallery with the same name in zenfolio's root group. The user has to
manage the galleries once they are stored """

# Suggested use: This script is meant for one time use. It copies all
# smugmug albums in one Zenfolio Group (it does not create hierarchies
# based on the category, and sub-category in Smugmug. Post sync, the
# user has to manually reorganize Zenfolio. 

# TODO

# 1. This script does not work well if there are multiple albums with
# the same name in smugmug. This is because it does not have any way
# to map a Zenfolio photoset to a smugmug gallery. A persistent
# mapping (either stored in a file, or maybe as description in a
# temporary zenfolio photoset :-) ) is required.

# 2. This script should ask for the zenfolio group in which the
# smugmug albums have to be stored. The current solution (picking up
# the first group) is a hack, bu tit works for me as I doint' have any
# useful galleries in Zenfolio.

# 3. There is some problem creating Zenfolio photosets with a forward
# slash in name or description, I get "HTTP 400" error in those cases,
# and have had to create the photosets with hand.

# 4. Handling of Photosets which have not been transferred
# completely. Generally two solutions come to mind - either delete
# these partial photosets, or upload only the files which are
# absent. So far, I have been manually deleting these photosets.

# 5. Create a hierarchical structure based on the categories and
# sub-categories within smugmug.

from optparse import OptionParser, OptionValueError
import urllib2
import smugmugapi.functional # download from svn at http://code.google.com/p/smugmug-api/
import zenfolioapi.functional

MAX_IMAGE_TRANSFER_TRIES = 2

def init_parser():
        
    parser = OptionParser (usage="%prog [--smuglogin login] [--smugpasswpord password] [--zenlogin login] [--zenpassword password] ")
    
    parser.add_option("--smuglogin",
                      action="store", type="string", dest="smug_login",
                      help="Smugmug Login")

    parser.add_option("--smugpassword",
                      action="store", type="string", dest="smug_password",
                      help="Smugmug Password")

    parser.add_option("--zenlogin",
                      action="store", type="string", dest="zen_login",
                      help="Zenfolio Login")

    parser.add_option("--zenpassword",
                      action="store", type="string", dest="zen_password",
                      help="Zenfolio Password")

    return parser


def z_create_gallery (zapi, root_id, title, caption):
    photoset_updater = {"Title":title, "Caption": caption}
    result = zapi.CreatePhotoSet (root_id, "Gallery", photoset_updater)
    photoset_id = result["result"]["Id"]
    upload_path = result["result"]["UploadUrl"]
    return photoset_id, upload_path

def s_get_all_images (sapi, session_id, album_id):
    result=sapi.images_get (SessionID=session_id, AlbumID=album_id)
    num_images = len(result.Images[0].Image)
    image_list = result.Images[0].Image
    return image_list

def s_download_image (sapi, session_id, image_id, image_key):
    # TBD: Ignore key. Refer http://www.dgrin.com/showthread.php?t=83919 for more details
    result=sapi.images_getInfo (SessionID=session_id, ImageID=image_id)
    original_url = result.Image[0]["OriginalURL"]
    file_name = result.Image[0]["FileName"]

    headers = {}
    headers['X-Smug-Version'] = sapi.version
    headers['X-Smug-SessionID'] = session_id
    
    req = urllib2.Request(original_url, headers=headers)
    opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=0))
    try:
        data = opener.open(req).read()
    except Exception, e:
        print e
        raise RuntimeError

    # TBD : check the format of last updated string
    return file_name, data

def transfer_image_s2z (sapi, session_id, image_id, image_key, zapi, upload_path, photoset_id):
    tries = 0
    while True:
        try:
            file_name, buffer, = s_download_image (sapi, session_id, image_id, image_key)
            zapi.uploads (upload_path, buffer, file_name)
        except Exception, e:
            tries += 1
            if tries >= MAX_IMAGE_TRANSFER_TRIES:
                raise RuntimeError ("max tries for image %s exceeded" % image_id)
            continue
        else:
            break            
    return
    
def transfer_albums (sapi, session_id, zapi):
    """ download a complete album """

    user_status = None

    # Get the location of the Zenfolio photo sets
    result=zapi.LoadGroupHierarchy ("cpandgp")
    root_zenfolio_id = result["result"]["Elements"][0]["Id"] # TBD : should come from command line
    root_element = result["result"]["Elements"][0]
    print "Loading the group hierarchy"
    
    # Step 1: fetch all albums
    result = sapi.albums_get(SessionID=session_id, Heavy = True) # TBD - Heavy does not seem to work
    album_list = result.Albums[0].Album
    album_set = set()
    album_title_list = []
    for album in album_list: 
        album_set.add (album["Title"])
        album_title_list.append (album["Title"])

    if len (album_set) != len (album_list):
        diff = []
        diff += album_title_list
        for l in list(album_set):
            diff.remove (l)
        print "There are some [%s] duplicate album names. Please rename accordingly" % diff

    for album in album_list:
        album_id = album["id"]
        album_title = album["Title"]
        # Step 3: Check if the album is present in zenfolio
        matches = []
        for element in root_element["Elements"]:
            if element ["Type"] == "Gallery" and element["$type"] == "PhotoSet":
                if element ["Title"] == album_title:
                    matches.append (element)
        # Get album details
        result = sapi.albums_getInfo(SessionID=session_id, AlbumID=album_id)
        album_description = result.Album[0]["Description"]        
        album_image_count = result.Album[0]["ImageCount"]

        if len (matches) == 0:
            # Step 4: Create a zenfolio gallery
            print "Creating Zenfolio Gallery : %s" % album_title
            zen_photoset_id, zen_upload_path = z_create_gallery (zapi, root_zenfolio_id, album_title, album_description)
        elif len (matches) == 1:
            zen_photoset_id, zen_upload_path = matches[0]["Id"], matches[0]["UploadUrl"] 
        else:
            print "Multiple albums with the name %s exist in Zenfolio. am using the first album to transfer all images" % album_title
            zen_photoset_id, zen_upload_path = matches[0]["Id"], matches[0]["UploadUrl"] # TBD: what about multiple matches

        if len (matches) > 0 and int(album_image_count) == matches[0]["PhotoCount"]:
            print "Album %s has already been transferred...skipping" % album_title
            continue # complete album is most likely updated. Ideally a check on 
        
        # Step 2: Ask the user if he wants to transfer the complete album
        while True and user_status != 'D':
            user_status=raw_input('Do you want to transfer album %s? (y(es)/n(o)/a(bort)/D(on\'t prompt) : ' % album_title)
            if not (user_status == 'y' or user_status == 'n' or user_status == 'a' or user_status == 'D'):
                print "Enter correct value."
                continue
            else:
                break

        if user_status == 'a':
            print "Aborting (without undo)....."
            break
        elif user_status == 'n':
            print "Skipping....."
            continue

        # Step 3: Check if the album exists in Zenfolio, with a similar number of pictures - TBD

        # Step 5: get all the imgaes (id)  from smugmug
        try:
            image_list = s_get_all_images (sapi, session_id, album_id)
        except Exception, e:
            print "Mostly empty album...ignoring"
            continue            
        
        # Step 6: transfer images to zenfolio
        print "Transfering approximately %s images" % len(image_list)
        for image in image_list:
            # TBD - there is no provision to sync partially synced albums
            if image.elementName == "Image":
                transfer_image_s2z (sapi, session_id, image["id"], image["Key"], zapi, zen_upload_path, zen_photoset_id)
                print ".",
            # transfer the images to smugmug

        print "Transfer complete"
    return None


def main():
    parser = init_parser()
    (options, args) = parser.parse_args()

    if not (options.smug_login or options.smug_password or 
            options.zen_login or options.zen_password or
            options.smug_gallery):
        parser.error ("Please provide all command line options")


    # Step 1. Login into Smugmug
    smugmug_api_key = "29qIYnAB9zHcIhmrqhZ7yK7sPsdfoV0e"  # API key
    sapi = smugmugapi.functional.SmugMugAPI (smugmug_api_key)
    result=sapi.login_withPassword (EmailAddress = options.smug_login, Password = options.smug_password)
    session_id = result.Login[0].Session[0]["id"]
    print "Logging into Smugmug"
                                    
    # Step 1.1 : Login into Zenfolio                                
    zapi = zenfolioapi.functional.ZenFolioAPI ()
    result=zapi.AuthenticatePlain (options.zen_login, options.zen_password, protocol="https")
    zapi.zen_token = result["result"]
    print "Logging into Zenfolio"

    # Step 2. Initiate transfer
    transfer_albums (sapi, session_id, zapi)

    return

# run the main if we're not being imported:
if __name__ == "__main__":
    main()

