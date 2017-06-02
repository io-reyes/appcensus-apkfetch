import pymysql
import logging
from datetime import datetime

_db = None
def init(host, db, user, password, force=False):
    global _db
    if(_db is None or force):
        _db = pymysql.connect(host=host, \
                              db=db, \
                              user=user, \
                              password=password)
        logging.info('DB host: %s | DB database: %s | DB user: %s' % (host, db, user))

def _query(query, *values):
    global _db
    assert _db is not None, 'No database connection established, must run init() first'

    cursor = _db.cursor()
    
    if(len(values) == 0):
        cursor.execute(query)
        logging.info('Query: %s' % query)
    else:
        cursor.execute(query, values)
        logging.info('Query: %s | Values: %s' % (query, str(values)))

    return cursor

def _commit():
    global _db
    assert _db is not None, 'No database connection established, must run init() first'
    _db.commit()
    logging.info('DB committed')

def _query_commit(query, *values):
    _query(query, *values) 
    _commit()

def insert_company(name, google_dev_id=None, company_type=None):
    company_type = 'dev' if google_dev_id is not None and company_type is None else company_type

    query = """INSERT INTO companies(googleDevId, commonName, type)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE
               commonName=%s, type=%s"""
    cursor = _query_commit(query, google_dev_id, name, company_type, name, company_type)

    # Get the primary key of the new row
    query = """SELECT id FROM companies
               WHERE commonName=%s"""
    cursor = _query(query, name)
    (pkey,) = cursor.fetchone()

    return pkey 

_epoch = datetime(1970, 1, 1)
def insert_app(dev_key, package_name, common_name, product_url=None, last_checked=None):
    # Set the timestamp to the current UTC time if not provided
    if(last_checked is None):
        global _epoch
        last_checked = int((datetime.utcnow() - _epoch).total_seconds())

    query = """INSERT INTO apps(packageName, commonName, devCompanyId, productUrl, timestampLastChecked)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               packageName=%s, commonName=%s, devCompanyId=%s, productUrl=%s, timestampLastChecked=%s"""
    cursor = _query_commit(query, package_name, common_name, dev_key, product_url, last_checked, \
                                  package_name, common_name, dev_key, product_url, last_checked)

    # Get the primary key of the new row
    query = """SELECT id FROM apps
               WHERE packageName=%s"""
    cursor = _query(query, package_name)
    (pkey,) = cursor.fetchone()

    return pkey

def insert_app_release(app_key, version_code, version_string, timestamp_publish, \
                       timestamp_download=None, has_iap=None, has_ads=None, social_nets=None, tested=0):
    query = """INSERT INTO appReleases(appId, versionCode, versionString, timestampPublish, timestampDownload, hasInAppPurchases, hasAds, socialNetworks, tested)
               VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               appId=%s, versionCode=%s, versionString=%s, timestampPublish=%s, timestampDownload=%s, hasInAppPurchases=%s, hasAds=%s, socialNetworks=%s, tested=%s"""
    cursor = _query_commit(query, \
                           app_key, version_code, version_string, timestamp_publish, timestamp_download, has_iap, has_ads, social_nets, tested, \
                           app_key, version_code, version_string, timestamp_publish, timestamp_download, has_iap, has_ads, social_nets, tested)

    # Get the primary key of the new row
    query = """SELECT id FROM appReleases
               WHERE appId=%s AND versionCode=%s"""
    cursor = _query(query, app_key, version_code)
    (pkey,) = cursor.fetchone()

    return pkey

def insert_categories(app_key, categories):
    if(len(categories) > 0):
        # Put any new categories in the table
        cat_values = ','.join(['(%s)' for cat in categories])
        query = """INSERT IGNORE INTO categories(categoryName)
                   VALUES %s""" % cat_values
        cursor = _query_commit(query, *categories)
        logging.info('Added %s to categories table' % str(categories))

        # Get the keys for this app's categories
        condition = ' OR '.join(['categoryName=%s' for cat in categories])
        query = """SELECT id FROM categories
                   WHERE %s""" % condition
        cursor = _query(query, *categories)
        new_cat_keys = [key[0] for key in cursor]
        logging.info('App %d has current category keys %s' % (app_key, str(new_cat_keys)))

        # Get the category keys already associated for this app
        query = """SELECT categoryId FROM appCategoriesMapping
                   WHERE appId=%s"""
        cursor = _query(query, app_key)
        old_cat_keys = [key[0] for key in cursor]
        logging.info('App %d has old category keys %s' % (app_key, str(old_cat_keys)))

        # Remove any category mappings that no longer apply
        remove_cat_keys = list(set(old_cat_keys) - set(new_cat_keys))
        if(len(remove_cat_keys) > 0):
            condition = ' OR '.join(['categoryId=%s' for cat_key in remove_cat_keys])
            query = """DELETE FROM appCategoriesMapping
                       WHERE appId=%d AND (%s)""" % (app_key, condition)
            cursor = _query_commit(query, *remove_cat_keys)
            logging.info('App %d lost old category keys %s' % (app_key, str(remove_cat_keys)))

        # Add any new category mappings
        add_cat_keys = list(set(new_cat_keys) - set(old_cat_keys))
        if(len(add_cat_keys) > 0):
            cat_values = ','.join(['(%d,%s)' % (app_key, '%s') for cat in add_cat_keys])
            query = """INSERT IGNORE INTO appCategoriesMapping(appId, categoryId)
                       VALUES %s""" % cat_values
            cursor = _query_commit(query, *add_cat_keys)
            logging.info('App %d gained new category keys %s' % (app_key, str(add_cat_keys)))

if __name__ == '__main__':
    logging.basicConfig(level=20)
    init('localhost', 'placeholder', 'placeholder', 'placeholder')

    dev_key = insert_company('Snoozecorp', google_dev_id='snoozecorpwhoa')
    app_key = insert_app(dev_key, 'com.snoozecorp.vungle', 'Snoozecorp Vungle')
    insert_categories(app_key, ['TEST_FOO', 'TEST_ZED'])


