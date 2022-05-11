import urllib.request
import urllib.error
import json
from typing import Union


def get_json(url: str) -> Union[int, dict]:
    try:
        response = urllib.request.urlopen(url)
    except urllib.error.HTTPError as error:
        return error.code

    return json.load(response)
