from lxml import html
import requests
import logging
import re
import urllib
from datetime import datetime

def get_app_page(package_name, base_url='https://play.google.com/store/apps/details?id=%s&hl=en', user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'):
    headers = {'User-Agent': user_agent}
    resp = requests.get(base_url % package_name, headers=headers)

    if(resp.status_code == 200):    # HTTP OK
        logging.info('Retrieved page for package "%s"' % package_name)
        
        tree = html.fromstring(resp.content)
        return tree 
    
    resp.raise_for_status()

def get_app_name(html_tree):
    name_elts = html_tree.xpath('//*[@id="body-content"]/div/div/div[1]/div[1]/div/div[1]/div/div[2]/h1/div')
    assert len(name_elts) == 1, '%d app name elements found, expecting exactly 1' % len(name_elts)
    name = name_elts[0].xpath('text()')[0].encode('utf-8')

    return name

def has_iap(html_tree):
    iap_elts = html_tree.xpath('//div[contains(@class, "inapp-msg")]/text()')
    return len(iap_elts) > 0

def get_dev_privacy(html_tree):
    dev_elts = html_tree.xpath('//a[contains(@class, "dev-link")]')

    for elt in dev_elts:
        link_text = elt.xpath('text()')[0]
        if(link_text.lower().strip() == 'privacy policy'):
            link = _clean_play_store_link(elt.get('href').encode('utf-8'))
            return link

    return None

def get_dev_email(html_tree):
    email_elts = html_tree.xpath('//a[contains(@class, "dev-link") and starts-with(@href, "mailto:")]')

    if(len(email_elts) == 1):
        href = email_elts[0].get('href').encode('utf-8')
        email = href.split(':', 1)[1]

        return email

    return None

def _clean_play_store_link(url):
    # Eliminate Play Store tracking BS surrounding the real URL
    # e.g., https://www.google.com/url?q=http://www.animocabrands.com&sa=D&usg=AFQjCNFsmmCpdweYyOvrV6bSNSZ-xWzEmg
    cleaned = urllib.unquote(url)
    cleaned = cleaned.replace('https://www.google.com/url?q=', '', 1)
    cleaned = cleaned.rsplit('&sa=')[0]

    return cleaned

def get_dev_website(html_tree):
    # Priority order, if some are unavailable:
    # 1. "Visit website" link
    # 2. "Privacy Policy" link
    # 3. Email link
    # 4. None
    dev_elts = html_tree.xpath('//a[contains(@class, "dev-link")]')

    link = None
    for elt in dev_elts:
        link_text = elt.xpath('text()')[0]
        if(link_text.lower().strip() == 'visit website'):
            link = _clean_play_store_link(elt.get('href').encode('utf-8'))
            break

    if(link is None):
        link = get_dev_privacy(html_tree)

    if(link is None):
        link = get_dev_email(html_tree)

    return link

def get_dev_id(html_tree):
    # Try the numeric dev ID, then the string one if necessary
    str_id_elts = html_tree.xpath('//a[contains(@class, "document-subtitle") and contains(@href, "/store/apps/dev")]')
    assert len(str_id_elts) == 1, '%d Dev IDs found, expecting exactly 1' % len(str_id_elts)
    href = str_id_elts[0].get('href').encode('utf-8')
    dev_id = href.rsplit('=', 1)[1]

    return dev_id

_epoch = datetime(1970, 1, 1)
def get_publish_timestamp_utc(html_tree):
    publish_elts = html_tree.xpath('//div[contains(@class, "content") and contains(@itemprop, "datePublished")]/text()')
    assert len(publish_elts) == 1, '%d Update dates found, expecting exactly 1' % len(publish_elts)

    publish_dt = datetime.strptime(publish_elts[0], '%B %d, %Y')    # Date example: May 1, 2016
    global _epoch
    timestamp = int((publish_dt - _epoch).total_seconds())
    
    return timestamp

def has_ads(html_tree):
    ad_elts = html_tree.xpath('//span[contains(@class, "ads-supported-label-msg")]/text()')
    return len(ad_elts) > 0

def is_free(html_tree):
    price_elts = html_tree.xpath('//div[contains(@class, "details-actions-right")]/span/span/button/span[2]/text()')
    assert len(price_elts) == 1, '%d Buy/Download buttons found, expecting exactly 1' % len(price_elts)
    return 'Install' in price_elts or 'Free' in price_elts

def get_categories(html_tree):
    cat_elts = html_tree.xpath('//a[contains(@class, "category")]/span/text()')
    return cat_elts

def is_family(html_tree):
    cat_elts = html_tree.xpath('//a[contains(@class, "category")]')
    cat_names = [x.get('href').split('/')[-1] for x in cat_elts]
    family_cats = [x for x in cat_names if x.startswith('FAMILY')]

    return len(family_cats) > 0

def get_icon_url(html_tree):
    icon_elts = html_tree.xpath('//div[contains(@class, "cover-container")]/img[contains(@class, "cover-image")]')
    assert len(icon_elts) == 1, '%d app icons found, expecting exactly 1' % len(icon_elts)
    icon_src = icon_elts[0].get('src').encode('utf-8')

    # Example value: //lh3.googleusercontent.com/ZZPdzvlpK9r_Df9C3M7j1rNRi7hhHRvPhlklJ3lfi5jk86Jd1s0Y5wcQ1QgbVaAP5Q=w300-rw
    # Need to prepend https:// and remove the =w300-rw
    if(icon_src.startswith('//')):
        icon_src = 'https:%s' % icon_src

    if(icon_src.endswith('=w300-rw')):
        icon_src = icon_src.rsplit('=', 1)[0]

    return icon_src

def get_install_count(html_tree):
    install_elts = html_tree.xpath('//div[contains(@itemprop, "numDownloads")]/text()')
    assert len(install_elts) == 1, '%d install count elements found, expecting exactly 1' % len(install_elts)
    install_str = install_elts[0].encode('utf-8')

    # Example: 1,000,000 - 5,000,000
    # Report the lower bound as an integer, in this case 1000000
    install_str = install_str.strip().replace(',', '').replace(' ', '')
    split_install_str = install_str.split('-')
    assert len(split_install_str) == 2, 'Install count string %s does not look like "1000000-5000000"' % install_str
    lower_count = int(split_install_str[0])

    return lower_count

def _test(package):
    page = get_app_page(package)

    print('-----')
    print('package: %s' % package)
    print('name: %s' % get_app_name(page))
    print('iap: %s' % has_iap(page))
    print('dev-site: %s' % get_dev_website(page))
    print('dev-email: %s' % get_dev_email(page))
    print('dev-privacy: %s' % get_dev_privacy(page))
    print('dev-id: %s' % get_dev_id(page))
    print('publish: %s' % get_publish_timestamp_utc(page))
    print('ads: %s' % has_ads(page))
    print('free: %s' % is_free(page))
    print('categories: %s' % get_categories(page))
    print('icon-url: %s' % get_icon_url(page))
    print('install-count: %d' % get_install_count(page))
    print('is-family: %s' % is_family(page))

if __name__ == '__main__':
    _test('com.rovio.angrybirds')
    _test('com.ustwo.monumentvalley')
    _test('com.google.android.apps.youtube.kids')
    _test('com.candidate.chestsimulatorforcr')
    _test('edu.berkeley.icsi.sensormonitor')
    _test('co.romesoft.toddlers.puzzle.pirates')
    _test('com.artygeekapps.app1095')
