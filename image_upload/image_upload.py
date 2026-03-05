from firebase_functions import https_fn
from firebase_admin import initialize_app, storage
from flask import Request
import uuid
import base64
import time   
from settings import *
from auth.auth_user_wrapper import uauth
import traceback

@uauth
@https_fn.on_request()
def uploadImages_fn(req: Request):
    try:
        if req.method != 'POST':
            return ("Method not allowed", 405)

        pdata = req.get_json()

        if "image_data" not in pdata:
            return {"couldn't read image data", 500}

        image_data = pdata["image_data"]

        download_urls = []          
        bucket = storage.bucket()
        for filename_key, imagedata_base64_value in image_data.items():
            lg.t("upload image ~ " + str(filename_key))
            imagedata_bytes = base64.b64decode(imagedata_base64_value)
            blob = bucket.blob(filename_key)
            blob.upload_from_string(imagedata_bytes, content_type="image/jpg")

            # GCS is eventually consistent: after uploading a blob, it may take a short moment before metadata is accessible (e.g., make_public() fails because the blob isn't fully propagated).
            # blob.reload(): explicitly refreshes the blob’s metadata. If the object isn’t "visible" yet (even though it was uploaded), it will raise an error.
            for _ in range(10):
                try:
                    blob.reload()  # refresh metadata
                    blob.make_public()
                    break
                except Exception as e:
                    time.sleep(0.5)  # wait and retry
                    download_urls.append(blob.public_url)

        response = {"success": True,
                    "download_urls":download_urls
                    }

        return response
    except Exception as e:
        lg.e("Exp ~ " + str(e) + " trace ~ " + str(traceback.format_exc()))
        return jsonify({'success': False,           
        'error': str(e),
        'trace': traceback.format_exc()
        }), 500   