from os import dup, listdir, makedirs
from os.path import isfile, join, sep, getsize, exists
import urllib
import urllib.request
import re
import json
import string
from unidecode import unidecode
from tqdm.std import tqdm
from fuzzywuzzy import fuzz
import imdb
import config

ia = imdb.IMDb()

META_DIR = join("scripts", "metadata")
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/search/movie?api_key=%s&language=en-US&query=%s&page=1"
TMDB_TV_URL = "https://api.themoviedb.org/3/search/tv?api_key=%s&language=en-US&query=%s&page=1"
TMDB_ID_URL = "https://api.themoviedb.org/3/find/%s?api_key=%s&language=en-US&external_source=imdb_id"
tmdb_api_key = config.tmdb_api_key

forbidden = ["the", "a", "an", "and", "or", "part", "vol", "chapter", "movie", "transcript"]

metadata = {}

def clean_name(name):
    # (Function content remains unchanged)
    ...

def average_ratio(n, m):
    # (Function content remains unchanged)
    ...

def roman_to_int(num):
    # (Function content remains unchanged)
    ...

def extra_clean(name):
    # (Function content remains unchanged)
    ...

def get_tmdb(name, type="movie"):
    # (Function content remains unchanged)
    ...

def get_tmdb_from_id(id):
    # (Function content remains unchanged)
    ...

def get_imdb(name):
    # (Function content remains unchanged)
    ...

def main():
    f = open('sources.json', 'r')
    data = json.load(f)

    for source in data:
        included = data[source]
        meta_file = join(META_DIR, source + ".json")
        if included == "true" and isfile(meta_file):
            with open(meta_file) as json_file:
                source_meta = json.load(json_file)
                metadata[source] = source_meta

    unique = []
    origin = {}
    for source in metadata:
        DIR = join("scripts", "unprocessed", source)
        files = [join(DIR, f) for f in listdir(DIR) if isfile(join(DIR, f)) and getsize(join(DIR, f)) > 3000]

        source_meta = metadata[source]
        for script in source_meta:
            name = re.sub(r'\([^)]*\)', '', script.strip()).lower()
            name = " ".join(name.split('-'))
            name = re.sub(r'['+string.punctuation+']', ' ', name)
            name = re.sub(' +', ' ', name).strip()
            name = name.split()
            name = " ".join(list(filter(lambda a: a not in forbidden, name)))
            name = "".join(name.split())
            name = roman_to_int(name)
            name = unidecode(name)
            unique.append(name)
            if name not in origin:
                origin[name] = {"files": []}
            curr_script = metadata[source][script]
            curr_file = join("scripts", "unprocessed", source, curr_script["file_name"] + ".txt")

            if curr_file in files:
                origin[name]["files"].append({
                    "name": unidecode(script),
                    "source": source,
                    "file_name": curr_script["file_name"],
                    "script_url": curr_script["script_url"],
                    "size": getsize(curr_file)
                })
            else:
                origin.pop(name)

    final = sorted(list(set(unique)))
    print(len(final))

    count = 0

    print("Get metadata from TMDb")

    for script in tqdm(origin):
        # Use original name
        name = origin[script]["files"][0]["name"]
        movie_data = get_tmdb(name)

        if movie_data:
            origin[script]["tmdb"] = movie_data
        else:
            # Try with cleaned name
            name = extra_clean(name)
            movie_data = get_tmdb(name)

            if movie_data:
                origin[script]["tmdb"] = movie_data
            else:
                # Try with TV search
                tv_data = get_tmdb(name, "tv")

                if tv_data:
                    origin[script]["tmdb"] = tv_data
                else:
                    print(name)
                    count += 1

    print(count)

    print("Get metadata from IMDb")

    count = 0
    for script in tqdm(origin):
        name = origin[script]["files"][0]["name"]
        movie_data = get_imdb(name)

        if not movie_data:
            name = extra_clean(name)
            movie_data = get_imdb(name)

            if not movie_data:
                print(name)
                count += 1
            else:
                origin[script]["imdb"] = movie_data
        else:
            origin[script]["imdb"] = movie_data

    print(count)

    # Use IMDb id to search TMDb
    count = 0
    print("Use IMDb id to search TMDb")

    for script in tqdm(origin):
        if "imdb" in origin[script] and "tmdb" not in origin[script]:
            # print(origin[script]["files"][0]["name"])
            imdb_id = "tt" + origin[script]["imdb"]["id"]
            movie_data = get_tmdb_from_id(imdb_id)
            if movie_data:
                origin[script]["tmdb"] = movie_data
            else:
                print(origin[script]["imdb"]["title"], imdb_id)
                count += 1

    with open(join(META_DIR, "clean_meta.json"), "w") as outfile:
        json.dump(origin, outfile, indent=4)

    print(count)

    count = 0
    print("Identify and correct names")

    for script in tqdm(origin):
        if "imdb" in origin[script] and "tmdb" in origin[script]:
            imdb_name = extra_clean(unidecode(origin[script]["imdb"]["title"]))
            tmdb_name = extra_clean(unidecode(origin[script]["tmdb"]["title"]))
            file_name = extra_clean(origin[script]["files"][0]["name"])

            if imdb_name != tmdb_name and average_ratio(file_name, tmdb_name) < 85 and average_ratio(file_name, imdb_name) > 85:
                imdb_id = "tt" + origin[script]["imdb"]["id"]
                movie_data = get_tmdb_from_id(imdb_id)
                if movie_data:
                    origin[script]["tmdb"] = movie_data
                else:
                    print(origin[script]["imdb"]["title"], imdb_id)
                    count += 1

            if imdb_name != tmdb_name and average_ratio(file_name, tmdb_name) > 85 and average_ratio(file_name, imdb_name) < 85:
                name = origin[script]["tmdb"]["title"]
                movie_data = get_imdb(name)

                if not movie_data:
                    name = extra_clean(name)
                    movie_data = get_imdb(name)

                    if not movie_data:
                        print(name)
                        count += 1
                    else:
                        origin[script]["imdb"] = movie_data
                else:
                    origin[script]["imdb"] = movie_data

    print(count)

    with open(join(META_DIR, "clean_meta.json"), "w") as outfile:
        json.dump(origin, outfile, indent=4)

if __name__ == '__main__':
    main()
