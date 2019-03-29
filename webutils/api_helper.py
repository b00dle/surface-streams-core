import requests
import os

SERVER_IP = "127.0.0.1"
SERVER_HTTP_PORT = 5000
SERVER_TUIO_PORT = 5001


def upload_image(path):
    global SERVER_IP
    r = requests.post(
        "http://" + SERVER_IP + ":" + str(SERVER_HTTP_PORT) + "/api/images",
        data={},
        json={"name": path.split("/")[-1]}
    )
    if r.status_code == 200:
        if r.headers['content-type'] == "application/json":
            data = r.json()
            uuid = data["uuid"]
            r = requests.put(
                "http://" + SERVER_IP + ":" + str(SERVER_HTTP_PORT) + "/api/images/" + uuid,
                files={'data': open(path, 'rb')}
            )
            if r.status_code == 200:
                return uuid
            else:
                raise ValueError("FAILURE: Image upload failed with code "+str(r.status_code)+"\n  > reason"+str(r.reason))
        else:
            raise ValueError("FAILURE: server reply format not supported.")
    else:
        raise ValueError("FAILURE: resource creation failed with code "+str(r.status_code)+"\n  > reason"+str(r.reason))


def download_image(uuid, img_folder="CLIENT_DATA/"):
    global SERVER_IP
    r = requests.get(
        "http://" + SERVER_IP + ":" + str(SERVER_HTTP_PORT) + "/api/images/" + uuid,
        stream=True
    )
    if r.status_code == 200:
        content_type = r.headers["content-type"].split("/")
        if len(content_type) != 2 or content_type[0] != "image":
            raise ValueError("FAILURE: Return type is no image")
        else:
            if not img_folder.endswith("/"):
                img_folder += "/"
            img_path = img_folder+uuid+"."+content_type[1]
            with open(img_path, 'wb') as img_file:
                for chunk in r.iter_content(1024):
                    img_file.write(chunk)
            return img_path
    else:
        raise ValueError("FAILURE: could not get image\n  > code" + str(r.status_code) + "\n  > reason" + str(r.reason))


def upload_tracking_config(uuid, tracking_server_url, path):
    if not os.path.exists(path):
        raise ValueError("FAILURE: tracking config does not exist.\n  > got"+path)
    r = requests.put(
        tracking_server_url + "/api/processes/" + uuid,
        files={'tracking_config': open(path, 'r')}
    )
    if r.status_code != 200:
        raise ValueError(
            "FAILURE: tracking config upload failed with code " + str(r.status_code)
            + "\n  > reason" + str(r.reason)
        )


def upload_tracking_resource(uuid, tracking_server_url, path):
    if not os.path.exists(path):
        raise ValueError("FAILURE: resource does not exist.\n  > got"+path)
    r = requests.put(
        tracking_server_url + "/api/processes/" + uuid + "/resources",
        files={'data': open(path, 'rb')}
    )
    if r.status_code != 200:
        raise ValueError(
            "FAILURE: resource upload failed with code " + str(r.status_code)
            + "\n  > reason" + str(r.reason)
        )