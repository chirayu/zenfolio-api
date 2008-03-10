''' API's to access Zenfolio.
For more information - http://code.google.com/p/zenfolio-api/

'''

import simplejson
import logging
import urllib
import urllib2
import email.Utils
import os

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

__version__ = "1"
__all__ = ('ZenFolioAPI', 'IllegalArgumentException', 'ZenFolioError',
           'set_log_level')

########################################################################
# Exceptions
########################################################################

class IllegalArgumentException(ValueError):
    '''Raised when a method is passed an illegal argument.
    
    More specific details will be included in the exception message
    when thrown.
    '''

class ZenFolioError(Exception):
    '''Raised when a ZenFolio method fails.
    
    More specific details will be included in the exception message
    when thrown.
    '''


class ZenFolioAPI (object):
    '''Implements the ZenFolio API

    Example zf = ZenFolioApi ()
    '''
    host = "www.zenfolio.com"
    api_path = "/zf/api/zfapi.asmx"
    user_agent = "Python API"

    def __init__ (self, fail_on_error = True):
        self.fail_on_error = fail_on_error
        self.__handlerCache={}
        self.zen_token = None
        return

    def __repr__ (self):
        return ("ZenFolio API")
    __str__ = __repr__


    def encode_and_sign(self, dictionary):
        '''URL encodes the data in the dictionary, and signs it using the
        given secret.
        '''
        
        #         dictionary = self.make_utf8(dictionary)
        #         dictionary['api_sig'] = self.sign(dictionary)
        return urllib.urlencode(dictionary)
    
    def __getattr__ (self, method):
        '''Handle all the SmugMug Calls'''
        
        # Refuse to act as a proxy for unimplemented special methods
        if method.startswith('__'):
            raise AttributeError("No such attribute '%s'" % method)

        if self.__handlerCache.has_key(method):
            # If we already have the handler, return it
            return self.__handlerCache[method]

        def handler (*args, **kwargs):
        
            params = {}
            params.update ({"params" : list(args)})
            params.update ({"method":method})
            params.update ({"id":"1"})

            body = simplejson.dumps (params)
            
            headers = {}
            headers['User-Agent'] = self.user_agent
            headers['Content-Type'] = 'application/json',
            headers["Content-Length"] = len(body)
            headers["Content-Type"] = "application/json"
            if self.zen_token:
                headers ["X-Zenfolio-Token"] = self.zen_token

            protocol = kwargs.get("protocol", "http")
            url = protocol + "://" + self.host + self.api_path
            req = urllib2.Request(url, data=body, headers=headers)
            opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=0))

            try:
                data = opener.open(req).read()
                LOG.debug ("RESPONSE: --\n%s\n--\n" % data)
                result = simplejson.loads(data)
                if self.fail_on_error:
                    ZenFolioAPI.testFailure(result, True)
            except Exception, e:
                raise RuntimeError

            return result

        self.__handlerCache[method] = handler

        return self.__handlerCache[method]


    @classmethod
    def testFailure(cls, rsp, exception_on_error=True):
        """Exit app if the rsp XMLNode indicates failure."""
        if rsp['error'] == None:
            return
        
        LOG.error(rsp['error'])
        if exception_on_error:
            raise ZenFolioError(rsp['error'])


    def upload(self, upload_path, file_name, date_modified=None):
        if not file_name:
            raise IllegalArgumentException("filename must be specified")

        file = open (file_name, "rb")
        size = os.path.getsize (file_name)
        file.seek(0)
        if date_modified:
            modified = email.Utils.formatdate (time.mktime (date_modified.timetuple()))
        else:
            modified = email.Utils.formatdate (os.path.getmtime (file_name))
                     
        fname = os.path.basename (file_name)

        self.uploads (upload_path, file.read(), fname, modified)

    def uploads(self, upload_path, data, fname, modified=None):
        """Upload a file to Zenfolio
        """

        headers = {}
        headers['User-Agent'] = self.user_agent
        headers['Content-Type'] = 'image/jpeg'
        headers['Content-Length'] = len(data)
        if self.zen_token:
            headers ["X-Zenfolio-Token"] = self.zen_token

        upload_url = 'http://' + "www.zenfolio.com" + upload_path
        url = upload_url + '?' + urllib.urlencode ([("filename", fname), ("modified", modified)])
        req = urllib2.Request(upload_url, data=data, headers=headers)
        opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=0))
        
        try:
            data = opener.open(req).read()
            LOG.debug ("RESPONSE: --\n%s\n--\n" % data)
            result = simplejson.loads(data)
            # TBD : check for erorr by checking the status of the HTTP message
        except Exception, e:
            print e
            raise RuntimeError

        return


def set_log_level(level):
    '''Sets the log level of the logger.
    
    >>> import smugmugapi
    >>> import logging
    >>> smugmugapi.set_log_level(logging.DEBUG)
    '''

    LOG.setLevel(level)

########################################################################
# Test functionality
########################################################################

def main():
    
    # initialize the API
    set_log_level (logging.DEBUG)
    zapi = ZenFolioAPI ()
    # login and create a session
    #result=sapi.login_withPassword (EmailAddress = "<your email>", Password = "<password>")

    # get group hierarchy
#    result=zapi.LoadGroupHierarchy ("mikewoods")
    
    #Login
    account = raw_input ("enter Zenfolio account name: ")
    password = raw_input ("enter Zenfolio account password: ")
    result=zapi.AuthenticatePlain (account, password, protocol="https")

    zapi.zen_token = result["result"]


    result=zapi.LoadGroupHierarchy ("cpandgp")

    root_id = result["result"]["Elements"][0]["Id"]

    # find the "Hahahahaha" gallery
    for element in result["result"]["Elements"][0]["Elements"]:
        if element["Title"] == "Hahahaha":
            test_gallery_id = element["Id"]

    zapi.LoadPhotoSet (test_gallery_id)

    zapi.upload (element["UploadUrl"], "/home/chirayu/tmp/j.jpg")

    photoset_updater = {"Title":"Hahahaha", "Caption": "Test Caption"}
    zapi.CreatePhotoSet (root_id, "Gallery", photoset_updater)
    
    return

# run the main if we're not being imported:
if __name__ == "__main__":
    main()

