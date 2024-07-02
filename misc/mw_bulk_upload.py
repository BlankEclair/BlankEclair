#!/usr/bin/env python3
import os
import sys
import time
import getpass
from urllib.parse import unquote
import requests

try:
    _, api_endpoint, username, summary, image_folder, image_offset = sys.argv
    image_offset = int(image_offset)
except ValueError:
    print(f"Usage: {sys.argv[0]} <api endpoint> <username> <summary> <image folder> <image offset>", file=sys.stderr)
    sys.exit(1)

session = requests.Session()
session.headers["User-Agent"] = "BulkUploadScript (https://meta.miraheze.org/wiki/User:BlankEclair; miraheze@blankeclair.slmail.me)"

def get_token(type: str) -> str:
    resp = session.post(api_endpoint, data={
        "action": "query",
        "meta": "tokens",
        "type": type,
        "format": "json",
    })
    return resp.json()["query"]["tokens"][f"{type}token"]

def login(login_token: str, username: str, password: str):
    resp = session.post(api_endpoint, data={
        "action": "login",
        "lgname": username,
        "lgpassword": password,
        "lgtoken": login_token,
        "format": "json",
    })
    try:
        assert resp.json()["login"]["result"] == "Success"
    except Exception:
        print(resp.text)
        raise

def upload(csrf_token: str, file_name: str, refetched_csrf: bool = False, ratelimit_waited: bool = False) -> str:
    with open(os.path.join(image_folder, file_name), "rb") as file:
        resp = session.post(api_endpoint, data={
            "action": "upload",
            "filename": unquote(file_name),
            "comment": summary,
            "ignorewarnings": 1,
            "token": csrf_token,
            "assert": "bot",
#            "assert": "user",
            "assertuser": username,
            "maxlag": 5,
            "format": "json",
        }, files={
            "file": (unquote(file_name), file, "multipart/form-data"),
        })

    json = resp.json()
    if not refetched_csrf and "error" in json and json["error"]["code"] == "badtoken":
        print("[*] Refetching CSRF token...")
        csrf_token = get_token("csrf")
        print("[*] Reattempting upload...")
        return upload(csrf_token, file_name, True, ratelimit_waited)
    elif not ratelimit_waited and "error" in json and json["error"]["code"] == "ratelimited":
        print("[*] Ratelimited, waiting 60 seconds...")
        time.sleep(60)
        print("[*] Reattempting upload...")
        return upload(csrf_token, file_name, refetched_csrf, True)

    try:
        assert json["upload"]["result"] == "Success"
    except Exception:
        print(resp.text)
        raise

    return csrf_token

print("[*] Getting login token...")
login_token = get_token("login")

print("[*} Logging in...")
login(login_token, username, getpass.getpass("Bot password: "))

print("[*] Getting CSRF token...")
csrf_token = get_token("csrf")

print("[*] Uploading files...")
files = os.listdir(image_folder)
files.sort()

for file_offset in range(image_offset - 1, len(files)):
    file_name = files[file_offset]
    print(f"[{file_offset + 1}/{len(files)}] {file_name}")

    csrf_token = upload(csrf_token, file_name)
