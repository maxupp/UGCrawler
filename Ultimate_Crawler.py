
# coding: utf-8

# # UGCrawler 1.0 alpha
# 
# This Notebook contains code fragments to crawl ultimate-guitar.com. It is far from finished but all the major components are there. 
# 
# Since it is not feasible for me to generate a complete rip, i am sharing this with all the guitarists out there who are pissed off by UG for any of the million reasons given. 
# 
# If you would like to contribute, by doing part of the crawl, of implementin a better selection logic, or in any other way, feel free to do so.

# In[1]:

from lxml import etree
import lxml.html
import string
import urllib
from time import sleep
import sys
import random
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from socket import timeout


# In[2]:

chars = ['0-9'] + list(string.ascii_lowercase)
chars = list(string.ascii_lowercase)

crawl_delay = 3

ua = UserAgent()


# In[3]:

class Proxifier():
    def __init__(self):
        self.proxies = []
        self.refuel()
        
    def refuel(self):
        # crawl some proxies
        proxies_req = urllib.request.Request('https://www.sslproxies.org/')
        proxies_req.add_header('User-Agent', ua.random)
        proxies_doc = urllib.request.urlopen(proxies_req).read().decode('utf8')

        soup = BeautifulSoup(proxies_doc, 'html.parser')
        proxies_table = soup.find(id='proxylisttable')

        # Save proxies in the array
        for row in proxies_table.tbody.find_all('tr'):
            self.proxies.append({
              'ip':   row.find_all('td')[0].string,
              'port': row.find_all('td')[1].string
            })
    
    def get_proxy(self):
        # Choose a random proxy, refuel if necessary
        if len(self.proxies) < 10:
            self.refuel()
                
        return random.choice(self.proxies)
    
    def drop_proxy(self, proxy):
        self.proxies = [x for x in self.proxies if x != proxy]


# In[4]:

proxifier = Proxifier()


# In[ ]:

# wrapper to encapsulate proxy logic and stuff
def get_html(url):
    proxy = proxifier.get_proxy()
    print('using proxy: {}'.format(proxy))
    
    # try 10 times with that proxy
    tries = 0
    while tries < 10:
        print('Attempt ' + str(tries) )
        req = urllib.request.Request(url)
        req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'http')
        req.add_header('User-Agent', 'ua.random')
        
        try:
            response = urllib.request.urlopen(req, timeout=5).read().decode('utf8')
            return response
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # site not found
                print('404')
                return '404'
            elif e.code == 403:
                # proxy banned, get new one
                print('banned: {}'.format(proxy))
                
                proxifier.drop_proxy(proxy)
                proxy = proxifier.get_proxy()
                tries = 0
            elif e.code == 502:
                print('refused: {}'.format(proxy))
                tries += 1
            elif e.code == 400:
                print('Bad request!')
                tries += 1
        except timeout:
            print('Timeout')
            proxifier.drop_proxy(proxy)
            proxy = proxifier.get_proxy()
            tries += 1
        except urllib.error.URLError as e:
            print(e.reason)
        except:
            print(sys.exc_info()[0])
            tries += 1
    
    # if 10 failures on same proxy for whatever reason, try again with a new one
    proxifier.drop_proxy(proxy)
    return get_html(url)
    


# In[ ]:

#proxifier.proxies = [{'ip': '217.61.14.44', 'port': '3128'} for i in range(10)]
get_html('http://www.httpbin.org/ip')


# In[ ]:

def get_band_urls(char):    
    base_url = 'http://www.ultimate-guitar.com/bands/{}.htm'
    
    htmlparser = etree.HTMLParser()
    
    band_dict = {}
    
    cnt = 0
    while True:
        postfix = '' if cnt == 0 else cnt
        response = get_html(base_url.format(char + str(postfix)))
        return response
        tree = etree.parse(response, htmlparser)

        # collect song links
        tab_table = tree.xpath('//*[contains(@class, "b3")]/../table[2]/tr/td[2]/a')
        
        # empty means no more pages
        if not tab_table:
            break
            
        for child in tab_table:
            band_dict[child.text[:-5]] = child.attrib['href']
        cnt += 1
        
    return band_dict


# In[ ]:

res = get_band_urls('0-9')


# In[19]:

res


# In[8]:

def get_artist_links(url):
    base_url = 'http://www.ultimate-guitar.com'

    # 2 schemes for paging:
    # https://www.ultimate-guitar.com/artist/3_inches_of_blood_9343?page=1
    #
    if url.endswith('.htm'):
        url = base_url + url[:-4] + '{}' + url[-4:]
    else:
        url = base_url + url + '?page={}'
        
    htmlparser = etree.HTMLParser()
    
    all_tabs_chords = []
    
    cnt = 0
    tries = 0
    while True:
        
        # page 0 exists and is pretty much page 1 without the album shit
        if cnt == 1:
            cnt = 2
            continue
            
        response = get_html(url.format(cnt))
        
        tree = etree.parse(response, htmlparser)
        
        # collect entries
        tab_table = tree.xpath("//td/b[./text()='Tab' or ./text()='tab']/../..")
        chords_table = tree.xpath("//td/b[./text()='Chords' or ./text()='chords']/../..")

        for song in tab_table:
            name = song.xpath('./td[1]/a[1]')[0].text    
            link = song.xpath('./td[1]/a[1]')[0].attrib['href']

            if not song.xpath('./td[2]/span[1]'):
                rating = 0
            else:
                rating = song.xpath('./td[2]/span[1]')[0].attrib['title']

            all_tabs_chords.append(
                {
                    'name': name,
                    'link': link,
                    'rating': float(rating),
                    'type': 'tab'
                }
            )
            
        for song in chords_table:
            name = song.xpath('./td[1]/a[1]')[0].text    
            link = song.xpath('./td[1]/a[1]')[0].attrib['href']

            if not song.xpath('./td[2]/span[1]'):
                rating = 0
            else:
                rating = song.xpath('./td[2]/span[1]')[0].attrib['title']

            all_tabs_chords.append(
                {
                    'name': name,
                    'link': link,
                    'rating': float(rating),
                    'type': 'chords'
                }
            )        
        cnt += 1
        
    return all_tabs_chords


# In[9]:

def get_print_version(url):
    tries = 0
    response = get_html(url)
    
    htmlparser = etree.HTMLParser()
    tree = etree.parse(response, htmlparser)

    # get link
    link = tree.xpath("//*[@id='print_link']")[0].attrib['href']

    response = get_html('http://tabs.ultimate-guitar.com{}'.format(link))

    ht = lxml.html.parse(response)
    return ht.xpath("//div[contains(@class, 'tb_ct')]")[0].text_content()


# In[10]:

def clean(s):
    return ' '.join(re.sub('[^a-zA-Z0-9\(\)\-\s"\'!?#$\+]', '', s).split())


# # UNLEASH THE SPIDER

# In[11]:

import re, os

highest_rated_only = True
target_dir = '/home/max/ssd_2/UG/'

for c in chars:
    # rip the band urls
    band_urls = get_band_urls(c)
    
    # rip the tabs for each band
    for artist, url in band_urls.items():
                    
        # make out dirs
        artist_folder_name = clean(artist)
        artist_dir = os.path.join(target_dir, c, artist_folder_name)
        
        if not os.path.exists(artist_dir):
            os.makedirs(artist_dir)
            os.makedirs(os.path.join(artist_dir, 'chords'))
            os.makedirs(os.path.join(artist_dir, 'tab'))
        else:
            # assume we finished crawling this artist
            continue
                       
        # rip
        print('Crawling {}...'.format(artist))
        song_links = get_artist_links(url)
        
        if len(song_links) == 0:
            print('\tNothing found!')
            continue

        
        artist_dict = {}
        artist_dict['chords'] = {}
        artist_dict['tab'] = {}
            
        # keep the highest rated version, factoring in rating count        
        for song_dict in song_links:
            t = song_dict['type']
            
            if highest_rated_only:
                cleaned_name = re.sub(r'\s\(ver\s\d+\)', '', song_dict['name'])
                
                if cleaned_name not in artist_dict[t].keys()                 or artist_dict[t][cleaned_name]['rating'] < song_dict['rating']:
                    artist_dict[t][cleaned_name] = song_dict
            else:
                artist_dict[t][song_dict['name']] = song_dict                
            
        # rip and write songs to drive
        for name, d in artist_dict['tab'].items():
            tab = get_print_version(d['link'])
            
            file_name = clean(name) + '.txt'
            
            with open(os.path.join(artist_dir, 'tab', file_name), 'w') as out:
                out.write(tab)
            
            
        for name, d in artist_dict['chords'].items():
            chords = get_print_version(d['link'])
            
            file_name = clean(name) + '.txt'
            
            with open(os.path.join(artist_dir, 'chords', file_name), 'w') as out:
                out.write(chords)

        

    sleep(5)


# In[ ]:

f


# In[12]:

response

