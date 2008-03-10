""" This file transfers a gallery from smugmug to zenfolio. It make a
gallery with the same name in zenfolio's root group. The user has to
manage the galleries once they are stored """

from optparse import OptionParser, OptionValueError
import urllib2

def init_parser():
        
    parser = OptionParser (usage="%prog [--smuglogin login] [--smugpasswpord password] [--zenlogin login] [--zenpassword password] [--smuggallery gallery]")
    
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

    parser.add_option("--smugalbum",
                      action="store", type="string", dest="smug_album",
                      help="The smugmug album that has to be transferred")

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
    opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1))    
    try:
        data = opener.open(req).read()
    except Exception, e:
        print e
        raise RuntimeError

    # TBD : check the format of last updated string
    return file_name, data

def transfer_image_s2z (sapi, session_id, image_id, image_key, zapi, upload_path, photoset_id):
    file_name, buffer, = s_download_image (sapi, session_id, image_id, image_key)
    zapi.uploads (upload_path, buffer, file_name)
    return
    
def transfer_albums (sapi, session_id, zapi):
    """ download a complete album """

    # Get the location of the Zenfolio photo sets
    result=zapi.LoadGroupHierarchy ("cpandgp")
    root_zenfolio_id = result["result"]["Elements"][0]["Id"]
    print "Loading the group hierarchy"


    # Step 1: fetch all albums
    result = sapi.albums_get(SessionID=session_id, Heavy = True) # TBD - Heavy does not seem to work
    album_list = result.Albums[0].Album
    for album in album_list:
        album_id = album["id"]
        album_title = album["Title"]
        result = sapi.albums_getInfo(SessionID=session_id, AlbumID=album_id)
        album_description = result.Album[0]["Description"]
        # Step 2: Ask the user if he wants to transfer the complete album
        while True:
            user_status=raw_input('Do you want to transfer album %s? (y(es)/n(o)/a(bort) : ' % album_title)
            if not (user_status == 'y' or user_status == 'n' or user_status == 'a'):
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
        # Step 4: Create a zenfolio gallery
        print "Creating Zenfolio Gallery : %s" % album_title
        zen_photoset_id, zen_upload_path = z_create_gallery (zapi, root_zenfolio_id, album_title, album_description)

        # Step 5: get all the imgaes (id)  from smugmug
        image_list = s_get_all_images (sapi, session_id, album_id)

        # Step 6: transfer images to zenfolio
        for image in image_list:
            if image.elementName == "Image":
                import pdb
                pdb.set_trace()
                transfer_image_s2z (sapi, session_id, image["id"], image["Key"], zapi, zen_upload_path, zen_photoset_id)
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

    import smugmugapi.functional
    import zenfolioapi.functional

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

