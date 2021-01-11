from pathlib import Path
import re
import argparse
import lxml.html
import requests
import urllib.request
from tqdm import tqdm


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_url(url, output_path):
    with DownloadProgressBar(unit="B", unit_scale=True, miniters=1, desc=url.split("/")[-1]) as t:
        urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)


def sanitize(string):
    return re.sub(r"[\?\:\s\n\t\r\?\/\-\!\@]+", "-", string)


def isID(string):
    videoMatch = re.findall(r"^\d{8}$", string)
    collectionMatch = re.findall(r"^[C]\d{5}$", string)
    if len(videoMatch) == 1 and len(collectionMatch) == 0:
        return {"type": "video", "id": string}
    elif len(videoMatch) == 0 and len(collectionMatch) == 1:
        return {"type": "collection", "id": string}
    else:
        raise argparse.ArgumentTypeError(
            "Not a valid pirsa.org video ID (--------) or collection ID (C-----) where - is a digit"
        )


def readCollection(collection_id):
    html = requests.get(f"http://pirsa.org/{collection_id}")
    doc = lxml.html.fromstring(html.content)
    name = doc.xpath("//h3/text()")[0]
    videoList = []
    i = 1
    while True:
        htmlp = requests.get(f"http://pirsa.org/{collection_id}/{i}")
        docp = lxml.html.fromstring(htmlp.content)
        ids = docp.xpath("//div[@class='search_results']/div[1]/b[1]/text()")
        if len(ids) > 0:
            videoList.extend(ids)
            i = i + 1
        else:
            break

    return {"name": sanitize(re.sub(r"[A-Z]{5}:C\d{5}\s-\s", "", name).strip()), "videoList": videoList}


def downloadVideo(video_id, path):
    html = requests.get(f"http://pirsa.org/{video_id}")
    doc = lxml.html.fromstring(html.content)
    name = doc.xpath("//div[@class='lecture_title']/text()")[0]
    download_url(f"http://streamer2.perimeterinstitute.ca/mp4-med/{video_id}.mp4", Path(f"{path}{sanitize(name)}.mp4"))


def main():
    parser = argparse.ArgumentParser(
        description="Simple downloader to get individual videos and collections from pirsa.org in python"
    )
    parser.add_argument(
        "id",
        metavar="ID",
        type=isID,
        help="A video ID or collection ID (starting with a C) from pirsa.org",
    )
    inputID = parser.parse_args().id

    if inputID["type"] == "collection":
        res = readCollection(inputID["id"])
        Path(res["name"]).mkdir(exist_ok=True)
        if Path(res["name"]).exists:
            for videoID in res["videoList"]:
                downloadVideo(videoID, f"./{res['name']}/")

    elif inputID["type"] == "video":
        downloadVideo(inputID["id"], "./")


if __name__ == "__main__":
    main()