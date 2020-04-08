from urllib.request import urlopen
from urllib.parse import quote
import urllib
import xml.etree.ElementTree


class Artist:
    def __init__(self, name, image, url):
        self.name = name
        self.image = image
        self.url = url

    def __eq__(self, other):
        if self.name == other.name:
            return True
        else:
            return False


class Track:
    def __init__(self, artist, name, image, url):
        self.artist = artist
        self.name = name
        self.image = image
        self.url = url

    def __eq__(self, other):
        if self.name == other.name and self.artist == other.artist:
            return True
        else:
            return False


def get_similar_from_array(apikey, array, method = "artist"):
    result = []
    com_array = []
    for item in array:
        artTrArr = item.split('-')
        artist_name = ""
        track_name = ""
        if len(artTrArr) >= 1:
            artist_name = artTrArr[0]
        if len(artTrArr) == 2:
            track_name = artTrArr[1]
        if len(artTrArr) > 2:
            continue

        artist_name = artist_name.strip()
        track_name = track_name.strip()

        print("artist_name = " + artist_name)
        print("track_name = " + track_name)

        similar = get_similar(apikey, artist_name, track_name, method)
        print(item)
        print("получено элементов: " + str(len(similar)))

        com_array.append(similar)

    if len(com_array) == 0:
        return []

    result = [] #com_array[0] если не добавляем ещё одного исполнителя/трек

    for test in com_array[0]:
        flag = True
        for array in com_array[1:]:
            if not test in array:
                flag = False
        if flag:
            result.append(test)
            

    print("Пересечение: " + str(len(result)) + " элементов")

    return result

def get_top_tracks(apikey, artist):
    print("artist name = " + str(artist))
    query = "http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist="
    query = query + artist[0] + "&api_key=" + apikey
    print(query)
    try:
    	req = urlopen(query)
    except BaseException:
    	print("Get Exception!!")
    	return []
        
    tree = xml.etree.ElementTree.parse(req)
    root = tree.getroot()
    if "ok" != root.get('status') or len(root) < 1:
        return []
        
    res_array = []

    for child in root[0]:
        name = child.find("name").text
        url = child.find("url").text
		#image_list = child.findall('.//image[@size="medium"}')
		#
		#if len(image_list):
		#	image = image_list[0].text
		#else:
		#	image = child.find("image").text
        track = Track(artist, name, 0, url)
        res_array.append(track)
        
    return res_array

def get_similar(apikey, artist, track ="", method = "artist"):
    query = "http://ws.audioscrobbler.com/2.0/?method=" + method + ".getsimilar&artist="
    query = query + quote(artist) + "&track=" + quote(track) + "&api_key=" + apikey

    print(query)

    #req = urlopen(query)
    try:
        req = urlopen(query)
    except BaseException:
        print("Get Exception!!")
        return []

    tree = xml.etree.ElementTree.parse(req)
    root = tree.getroot()

    if "ok" != root.get('status') or len(root) < 1:
        return []

    res_array = []
    if method == "artist":
        for child in root[0]:
            name = child.find("name").text
            url = child.find("url").text
            image_list = child.findall('.//image[@size="large"]')
            if len(image_list):
                image = image_list[0].text
            else:
                image = child.find("image").text
            artist = Artist(name, image, url)
            res_array.append(artist)
    elif method == "track":
        for child in root[0]:
            name = child.find("name").text
            url = child.find("url").text
            artist = child.find("artist").find("name").text
            image_list = child.findall('.//image[@size="large"]')
            if len(image_list):
                image = image_list[0].text
            else:
                image = child.find("image").text
            track = Track(artist, name, image, url)
            res_array.append(track)

    return res_array
