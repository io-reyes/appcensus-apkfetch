import os
import logging
import time
import publicmeta

from googleplay_api.googleplay import GooglePlayAPI,LoginError

api = None
def init_api(acct_email, acct_password, gsf, auth_sub_token=None, max_attempts=15, cooldown_secs=10):
    global api
    assert max_attempts > 0, 'max_attempts was %d, must be greater than 0' % max_attempts
    assert cooldown_secs > 0, 'cooldown_secs was %d, must be greater than 0' % cooldown_secs

    if api is None:
        # Ensure we have all the credentials we need
        assert acct_email is not None, 'Account email address is required'
        assert acct_password is not None, 'Account password is required'
        assert gsf is not None, 'Google Services Framework ID is required'

        # Authenticate the API, keep trying until it works
        api = GooglePlayAPI(androidId=gsf)

        for attempt in range(max(1, max_attempts)):
            attempt = attempt + 1
            try:
                api.login(email=acct_email, password=acct_password, authSubToken=auth_sub_token)
                logging.info('Successfully logged in as %s' % acct_email)
                return
            except LoginError as e:
                logging.warning('BadAuthentication on attempt %d/%d' % (attempt, max_attempts))

                if(attempt == max_attempts):
                    raise e

                logging.warning('Retrying authentication in %d seconds' % cooldown_secs)
                time.sleep(cooldown_secs)

def get_metadata(package):
    # Ensure the API is set
    global api
    assert api is not None, 'Need to call init_api() before attempting to get info about an APK'

    # Get info about the app (authenticated)
    metadata = api.details(package)
    metadata = api.toDict(metadata)

    # Get info about the app (public)
    metadata['public-meta'] = get_public_metadata(package)

    return metadata

def get_public_metadata(package):
    app_page = publicmeta.get_app_page(package)
    metadata = { \
        'iap' : publicmeta.has_iap(app_page), \
        'devSite' : publicmeta.get_dev_website(app_page), \
        'devPrivacy' : publicmeta.get_dev_privacy(app_page), \
        'devEmail' : publicmeta.get_dev_email(app_page), \
        'devId' : publicmeta.get_dev_id(app_page), \
        'publishTimestamp' : publicmeta.get_publish_timestamp_utc(app_page), \
        'ads' : publicmeta.has_ads(app_page), \
        'free' : publicmeta.is_free(app_page), \
        'categories' : publicmeta.get_categories(app_page), \
        'appIcon': publicmeta.get_icon_url(app_page), \
        'installs': publicmeta.get_install_count(app_page), \
        'family': publicmeta.is_family(app_page)
    }

    return metadata

def get_apk(package, version_code=None, outdir=None):
    # Ensure the output directory exists if it's specified
    assert outdir is None or os.path.isdir(outdir), 'Output directory %s does not exist' % outdir

    # Get info about the app if no version code was provided
    if(version_code is None):
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
    
    logging.info('Saved app to %s' % filepath)
