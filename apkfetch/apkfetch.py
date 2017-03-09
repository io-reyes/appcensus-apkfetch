import os

from googleplay_api.googleplay import GooglePlayAPI

api = None
def init_api(acct_email, acct_password, gsf):
    global api

    if api is None:
        # Ensure we have all the credentials we need
        assert acct_email is not None, 'Account email address is required'
        assert acct_password is not None, 'Account password is required'
        assert gsf is not None, 'Google Services Framework ID is required'

        # Authenticate the API
        api = GooglePlayAPI(androidId=gsf)
        api.login(email=acct_email, password=acct_password)

def get_metadata(package):
    # Ensure the API is set
    global api
    assert api is not None, 'Need to call init_api() before attempting to get info about an APK'

    # Get info about the app
    metadata = api.details(package)
    return api.toDict(metadata)

def get_apk(package, outdir=None):
    # Ensure the output directory exists if it's specified
    assert outdir is None or os.path.isdir(outdir), 'Output directory %s does not exist' % outdir

    # Get info about the app
    store_listing = get_metadata(package)
    assert 'docV2' in store_listing, 'Store listing unavailable for %s' % package
    store_listing = store_listing['docV2']

    assert 'details' in store_listing
    assert 'appDetails' in store_listing['details'], 'App details unavailable for %s' % package
    assert 'versionCode' in store_listing['details']['appDetails'], 'Version code does not exist for %s' % package
    assert 'versionString' in store_listing['details']['appDetails'], 'Version string does not exist for %s' % package
    version_code = store_listing['details']['appDetails']['versionCode']

    # Download the app as <packagename>-<versioncode>.apk
    filename = '%s-%d.apk' % (package, version_code)
    filepath = os.path.join(outdir, filename) if outdir is not None else filename
    with open(filepath, 'wb') as f:
        f.write(api.download(package, version_code))
    
    print('Saved app to %s' % filepath)
