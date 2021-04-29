#! /usr/bin/python
# This script can be used when you need to export multiple files for each item. 

from omekaclient import OmekaClient
import csv
import json
import math
import time
import pandas as pd
import requests
import urllib3
import urllib.request
import ast
import ssl
'''
Extract top-level metadata and element_texts from items returned by
Omeka 2.x API request, and then write to a CSV file. Intended for
requests to items, collections, element sets, elements, files, & tags.
'''

endpoint = ''
apikey = ''
resource = 'items'

def request(query={}):
    ssl._create_default_https_context = ssl._create_unverified_context
    response, content = OmekaClient(endpoint, apikey).get(resource, None, query)
    if response.status != 200:
        print(response.status, response.reason)
        exit()
    else:
        print(response.status, response.reason)
        return response, content

def unicodify(v):
    if type(v) is bool or type(v) is int:
        v = str(v)
        return v
    else:
       return v

def get_all_pages(pages):
    global data
    page = 1
    while page <= pages:
        print('Getting results page ' + str(page) + ' of ' + str(pages) + ' ...')
        response, content = request({'page': str(page), 'per_page': '50'})
        data.extend(json.loads(content))
        page += 1
        time.sleep(2)

ssl._create_default_https_context = ssl._create_unverified_context
# make initial API request; get max pages
response, content = request()
pages = int(math.ceil(float(response['omeka-total-results'])/50))

# declare global variables; get all pages
fields = []
data = []
get_all_pages(pages)

for D in data:
    if 'tags' in D and D['tags']:
        tags = [ d['name'] for d in D['tags'] ]
        D['tags'] = ', '.join(tags)
    if 'element_texts' in D:
        for d in D['element_texts']:
            k = d['element']['name']
            v = d['text']
            D[k] = v
    for k, v in list(D.items()):
        D[k] = unicodify(v)
        if D[k] and type(v) is dict:
            for key, value in v.items():
                D[k + '_' + key] = unicodify(D[k][key])
        if type(v) is list or type(v) is dict:
            del D[k] 
        if v == None:
            del D[k]
    for k in D.keys():
        if k not in fields: fields.append(k)

df = pd.DataFrame(data)
df.to_csv('omeka-data-no-files.csv', index=False)
print('File created: omeka-data-no-add.csv')

#filter df for those that are in the climate stories collection 
#df = df.loc[df['collection_id'] == "4"]

# to request files and save in df
files_url = []
for index, row in df.iterrows():
    id = row["id"]
    url = row['files_url']
    go_url = urllib.request.urlopen(url)
    review = go_url.read()
    files_json = {}
    for i in json.loads(review): files_json.update(i)
    if 'file_urls' not in files_json.keys(): 
        file = ""
        files_url.append(file)
        print("no url for "+ id)
    else:
        # load the json data
        items = json.loads(review)

        count = 0
        urls = []
        for keyval in items:
            if keyval['file_urls']:
                filesurl = keyval['file_urls']
                file = filesurl['original']
                print("found url for "+ id + " " + str(count))
                if file.find('/'):
                    filename = file.rsplit('/', 1)[1]
                    file_name_full = filename.split(".")
                    file_name = file_name_full[0]
                    file_type = file_name_full[1]
                    new_file_name = "files/" + id + "_" + str(count) + "." + file_type
                    urls.append(new_file_name)
                    response = requests.get(file)
                    with open(new_file_name, "wb") as download:
                        download.write(response.content)
                        print("files saved for "+ id + ": " + new_file_name)
                        count+=1 
        files_url.append(urls)
#print(files_url)
df['file'] = files_url
df.to_csv('omeka-data-files.csv', index=False)
print('File created: omeka-data-files.csv')
