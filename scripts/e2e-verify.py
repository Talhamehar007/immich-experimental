#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for Immich-Experimental
Verifies core APIs, Uploads (JPEG, HEIC, MP4), Streaming, Search, Web Chunks, and Isolation.
"""
import sys
import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from io import BytesIO

BASE_URL = "http://127.0.0.1:3283/api"
WEB_URL = "http://127.0.0.1:3283"
API_KEY = "test_e2e_api_key_immich_exp_990pro"
COOKIE = "immich_access_token=test_session_cookie_12345"

passed_tests = 0
failed_tests = 0

def test(name):
    def decorator(fn):
        global passed_tests, failed_tests
        print(f"[*] Testing {name}...", end=" ", flush=True)
        try:
            fn()
            print("\033[92mPASS\033[0m")
            passed_tests += 1
        except Exception as e:
            print(f"\033[91mFAIL\033[0m: {e}")
            failed_tests += 1
    return decorator

def req(path, method="GET", data=None, headers=None, expect_status=200):
    url = f"{BASE_URL}{path}" if path.startswith("/") else path
    h = {"x-api-key": API_KEY, "User-Agent": "Immich-E2E-Tester"}
    if headers:
        h.update(headers)
    
    body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            body = json.dumps(data).encode("utf-8")
            h["Content-Type"] = "application/json"
        elif isinstance(data, bytes):
            body = data

    request = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.getcode()
            resp_body = response.read()
            if status != expect_status:
                raise AssertionError(f"Expected status {expect_status}, got {status}")
            return status, resp_body, response.headers
    except urllib.error.HTTPError as e:
        resp_body = e.read()
        if e.code == expect_status:
            return e.code, resp_body, e.headers
        raise AssertionError(f"HTTP {e.code}: {resp_body.decode('utf-8', errors='ignore')}")

# Multipart upload helper
def upload_file(filename, file_bytes, is_favorite=False, extra_fields=None):
    boundary = "----WebKitFormBoundary" + str(int(time.time() * 1000))
    body = bytearray()
    
    fields = {
        "fileCreatedAt": "2026-10-16T04:00:00.000Z",
        "fileModifiedAt": "2026-10-16T04:00:00.000Z",
        "isFavorite": "true" if is_favorite else "false",
    }
    if extra_fields:
        fields.update(extra_fields)
        
    for k, v in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{v}\r\n".encode("utf-8"))
        
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="assetData"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return req("/assets", method="POST", data=bytes(body), headers=headers, expect_status=201)

print("\n=======================================================")
print("   IMMICH-EXPERIMENTAL END-TO-END VERIFICATION SUITE  ")
print("=======================================================\n")

uploaded_asset_ids = []

# 1. Server Endpoints
@test("Server Version (GET /server/version)")
def test_server_version():
    status, body, _ = req("/server/version")
    v = json.loads(body)
    assert v["major"] == 3 and v["minor"] == 3 and v["patch"] == 3, f"Unexpected version: {v}"

@test("Server Config (GET /server/config)")
def test_server_config():
    status, body, _ = req("/server/config")
    c = json.loads(body)
    assert "loginPageMessage" in c or "trash" in c

@test("Server Features (GET /server/features)")
def test_server_features():
    status, body, _ = req("/server/features")
    f = json.loads(body)
    assert f.get("smartSearch") is True
    assert f.get("facialRecognition") is True

@test("Server Media Types (GET /server/media-types)")
def test_media_types():
    status, body, _ = req("/server/media-types")
    mt = json.loads(body)
    assert ".mp4" in mt["video"]
    assert ".heic" in mt["image"]

# 2. Auth & User Endpoints
@test("Current User Info (GET /users/me)")
def test_users_me():
    status, body, _ = req("/users/me")
    u = json.loads(body)
    assert u["email"] == "abutalha34540@gmail.com"
    assert u["isAdmin"] is True

@test("Cookie Auth Check (GET /users/me with cookie)")
def test_cookie_auth():
    status, body, _ = req("/users/me", headers={"Cookie": COOKIE, "x-api-key": ""})
    u = json.loads(body)
    assert u["email"] == "abutalha34540@gmail.com"

# 3. Bulk Upload Pre-Check
@test("Bulk Upload Check (POST /assets/bulk-upload-check)")
def test_bulk_upload_check():
    data = {"assets": [{"id": "dummy.jpg", "checksum": "aabbccddeeff00112233445566778899aabbccdd"}]}
    status, body, _ = req("/assets/bulk-upload-check", method="POST", data=data)
    res = json.loads(body)
    assert len(res["results"]) == 1
    assert res["results"][0]["action"] == "accept"

# 4. Asset Uploads (JPEG, HEIC, MP4)
@test("Asset Upload - JPEG Image")
def test_upload_jpeg():
    from PIL import Image
    buf = BytesIO()
    img = Image.new("RGB", (200, 200), color=(0, 128, 255))
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()
    
    fname = f"e2e-test-{int(time.time())}.jpg"
    status, body, _ = upload_file(fname, jpeg_bytes)
    res = json.loads(body)
    assert res["status"] == "created"
    assert "id" in res
    uploaded_asset_ids.append(res["id"])

@test("Asset Duplicate Rejection (POST /assets duplicate)")
def test_upload_duplicate():
    if not uploaded_asset_ids:
        return
    # Re-upload the same file using cookie
    from PIL import Image
    buf = BytesIO()
    img = Image.new("RGB", (200, 200), color=(0, 128, 255))
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()
    fname = "duplicate-test.jpg"
    
    # upload duplicate should return 200 status duplicate
    boundary = "----WebKitFormBoundary" + str(int(time.time() * 1000))
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="fileCreatedAt"\r\n\r\n2026-10-16T04:00:00.000Z\r\n'.encode("utf-8"))
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="fileModifiedAt"\r\n\r\n2026-10-16T04:00:00.000Z\r\n'.encode("utf-8"))
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="isFavorite"\r\n\r\nfalse\r\n'.encode("utf-8"))
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="assetData"; filename="{fname}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
    body.extend(jpeg_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    status, body, _ = req("/assets", method="POST", data=bytes(body), headers=headers, expect_status=200)
    res = json.loads(body)
    assert res["status"] == "duplicate"
    assert res["id"] == uploaded_asset_ids[0]

@test("Asset Upload - HEIC Image (Testing Native Decoder Fallback)")
def test_upload_heic():
    sample_heic = "/Volumes/990Pro/abu/immich-experimental-data/library/admin/2025/11/27/IMG_4029.heic"
    if os.path.exists(sample_heic):
        with open(sample_heic, "rb") as f:
            heic_bytes = f.read()
        fname = f"e2e-heic-{int(time.time())}.heic"
        status, body, _ = upload_file(fname, heic_bytes)
        res = json.loads(body)
        assert res["status"] in ("created", "duplicate")
        if res.get("id"):
            uploaded_asset_ids.append(res["id"])

# 5. Asset Retrieval, Thumbnails & Streaming
@test("Asset Metadata Retrieval (GET /assets/:id)")
def test_asset_metadata():
    if not uploaded_asset_ids:
        return
    asset_id = uploaded_asset_ids[0]
    status, body, _ = req(f"/assets/{asset_id}")
    a = json.loads(body)
    assert a["id"] == asset_id
    assert a["type"] == "IMAGE"

@test("Asset Download Original (GET /assets/:id/original)")
def test_asset_download_original():
    if not uploaded_asset_ids:
        return
    asset_id = uploaded_asset_ids[0]
    status, body, headers = req(f"/assets/{asset_id}/original")
    assert len(body) > 100

@test("Video Playback Partial Content (HTTP 206 Range Request)")
def test_video_playback_range():
    # Find an existing video asset
    status, body, _ = req("/search/metadata", method="POST", data={"type": "VIDEO", "size": 1})
    res = json.loads(body)
    assets = res.get("assets", {}).get("items", [])
    if not assets:
        return
    vid_id = assets[0]["id"]
    status, body, headers = req(f"/assets/{vid_id}/video/playback", headers={"Range": "bytes=0-1024"}, expect_status=206)
    assert len(body) == 1025
    assert "bytes 0-1024" in headers.get("Content-Range", "")

# 6. Timeline & Search
@test("Timeline Buckets (GET /timeline/buckets)")
def test_timeline_buckets():
    status, body, _ = req("/timeline/buckets?size=MONTH")
    buckets = json.loads(body)
    assert isinstance(buckets, list)
    assert len(buckets) > 0

@test("CLIP Semantic Search (GET /search/smart)")
def test_smart_search():
    status, body, _ = req("/search/smart?query=nature")
    res = json.loads(body)
    assert "assets" in res

@test("People Search (GET /search/person)")
def test_search_person():
    status, body, _ = req("/search/person")
    persons = json.loads(body)
    assert isinstance(persons, list)

# 7. Album Lifecycle
@test("Album Lifecycle (Create, Add Asset, Delete)")
def test_album_lifecycle():
    if not uploaded_asset_ids:
        return
    # Create
    status, body, _ = req("/albums", method="POST", data={"albumName": f"E2E Album {int(time.time())}"}, expect_status=201)
    album = json.loads(body)
    album_id = album["id"]
    
    # Add asset
    status, body, _ = req(f"/albums/{album_id}/assets", method="PUT", data={"ids": [uploaded_asset_ids[0]]})
    
    # Delete
    status, body, _ = req(f"/albums/{album_id}", method="DELETE", expect_status=204)

# 8. Web Frontend Routes & Chunks Integrity
@test("Web Root Route (GET /)")
def test_web_root():
    status, body, headers = req(WEB_URL + "/", expect_status=200)
    assert b"<!DOCTYPE html>" in body or b"<html" in body

@test("Web Archive Route (GET /archive)")
def test_web_archive():
    status, body, headers = req(WEB_URL + "/archive", expect_status=200)
    assert b"<!DOCTYPE html>" in body or b"<html" in body

@test("Web Favorites Route (GET /favorites)")
def test_web_favorites():
    status, body, headers = req(WEB_URL + "/favorites", expect_status=200)
    assert b"<!DOCTYPE html>" in body or b"<html" in body

@test("Web Locked Folder Route (GET /locked)")
def test_web_locked():
    status, body, headers = req(WEB_URL + "/locked", expect_status=200)
    assert b"<!DOCTYPE html>" in body or b"<html" in body

@test("Web Chunk Backwards Compatibility (GET /_app/immutable/nodes/15.DN9apBIS.js)")
def test_chunk_alias_15():
    status, body, headers = req(WEB_URL + "/_app/immutable/nodes/15.DN9apBIS.js", expect_status=200)
    assert "javascript" in headers.get("Content-Type", "")

@test("Web Chunk Backwards Compatibility (GET /_app/immutable/nodes/18.D5S2xV68.js)")
def test_chunk_alias_18():
    status, body, headers = req(WEB_URL + "/_app/immutable/nodes/18.D5S2xV68.js", expect_status=200)
    assert "javascript" in headers.get("Content-Type", "")

@test("Web Chunk Backwards Compatibility (GET /_app/immutable/nodes/20.D6DUE0mA.js)")
def test_chunk_alias_20():
    status, body, headers = req(WEB_URL + "/_app/immutable/nodes/20.D6DUE0mA.js", expect_status=200)
    assert "javascript" in headers.get("Content-Type", "")

@test("Web Worker Chunk (GET /_app/immutable/workers/hash-file-CeWQn_WI.js)")
def test_worker_chunk():
    status, body, headers = req(WEB_URL + "/_app/immutable/workers/hash-file-CeWQn_WI.js", expect_status=200)
    assert "javascript" in headers.get("Content-Type", "")

@test("Missing Asset Proper 404 (GET /_app/immutable/non-existent.js -> HTTP 404)")
def test_missing_asset_404():
    status, body, _ = req(WEB_URL + "/_app/immutable/non-existent.js", expect_status=404)
    assert b"Not Found" in body

# Summary
print("\n=======================================================")
print(f"   TOTAL TESTS: {passed_tests + failed_tests}")
print(f"   PASSED:      \033[92m{passed_tests}\033[0m")
print(f"   FAILED:      \033[91m{failed_tests}\033[0m")
print("=======================================================\n")

if failed_tests > 0:
    sys.exit(1)
sys.exit(0)
