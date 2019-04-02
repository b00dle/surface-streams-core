"""
This script holds convenience functionality to access http functionality on Surface Streams 2.0 server and Surface
Streams 2.0 remote tracking server. The respective repos can be found at
https://github.com/b00dle/surface-streams-server and https://github.com/b00dle/surface-streams-remote-tracker
"""
import requests
import os

SERVER_IP = "127.0.0.1"
SERVER_HTTP_PORT = 5000
SERVER_TUIO_PORT = 5001


def upload_image(path):
    """
    Helper function to upload image resource to Surface Streams 2.0 server using ReST API calls. After the upload is
    done the resource can be reached at: "http://" + SERVER_IP + ":" + str(SERVER_HTTP_PORT) + "/api/images/{uuid}",
    where {uuid} corresponds to the return value of this function. For further details of ReST API structure of Surface
    Streams 2.0 server and further info see https://github.com/b00dle/surface-streams-server.

    :param path: filepath to the image resource

    :return: uuid of the resource created on the server
    """
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
    """
    Helper function to download an image resource from the Surface Streams 2.0 server using ReST API calls. After
    downloading, the image will be saved to: img_filder/uuid.<type>, where <type> is retrieved from content_type of
    image resource returned over http. For further details of ReST API structure of Surface Streams 2.0 server and
    further info see https://github.com/b00dle/surface-streams-server.

    :param uuid: uuid of the image resource on the server

    :return: the path of the saved image resource
    """
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
    """
    Helper function to upload a tracking_config JSON formatted file to a Surface Streams remote tracking server. For
    more info on Surface Streams 2.0 remote tracker see https://github.com/b00dle/surface-streams-remote-tracker.

    :param uuid: uuid of the remote tracking session (assigned by server), see webutils/remote_tracking_session.py

    :param tracking_server_url: full address of the remote tracking service

    :param path: path to the JSON formatted config file

    :return: None
    """
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
    """
    Uploads a resource for a remote tracking session. This could for instance be an image referenced by the JSON
    formatted tracking config file for the respective session. For more info on Surface Streams 2.0 remote tracker see
    https://github.com/b00dle/surface-streams-remote-tracker.

    :param uuid: uuid of the remote tracking session (assigned by server), see webutils/remote_tracking_session.py

    :param tracking_server_url: full address of the remote tracking service

    :param path: path to the JSON formatted config file

    :return: None
    """
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