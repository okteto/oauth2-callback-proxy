from flask import Flask, render_template, request, make_response, jsonify, g, redirect, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
    UserMixin
)
from oauthlib.oauth2 import WebApplicationClient
from oauthlib.common import add_params_to_uri

import requests
import json
import os
import socket
import random
import json
import collections
import base64

GOOGLE_CLIENT_ID = os.environ.get("OAUTH2_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("OAUTH2_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)
PUBLIC_URL = os.environ.get("PUBLIC_URL", None)

client = WebApplicationClient(GOOGLE_CLIENT_ID)
app = Flask(__name__)

@app.route("/oauth2")
def login():
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    redirect_url=PUBLIC_URL

    state = request.args.get("state")
    if not state:
        return "empty state", 400

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=redirect_url,
        scope=["openid", "email", "profile"],
        state=state
    )

    print("oauth2 - redirecting to " + request_uri + " with redirect_url " + redirect_url)
    return redirect(request_uri)

@app.route("/oauth2/callback")
def callback():
    request_url = request.url.replace('http://', 'https://')
    request_base_url = request.base_url.replace('http://', 'https://')
    
    code = request.args.get("code")
    state = request.args.get("state")
    if not state:
        return "empty state", 400

    decoded_state_json = json.loads(base64.b64decode(state))
    print(decoded_state_json)

    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
    token_endpoint,
    authorization_response=request_url,
    redirect_url=request_base_url,
    code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400

    print("successfully authenticated " + users_email)
    redirect_url=decoded_state_json["prd"]

    user = dict(id_=unique_id, name=users_name, email=users_email, profile_pic=picture)
    state = base64.b64encode(json.dumps(user).encode("utf-8"))
    
    params = [('state', state)]
    redirect_url_with_state = add_params_to_uri(redirect_url, params)
    return redirect(redirect_url_with_state)

if __name__ == "__main__":
    extra_files = []
    if "development" == os.getenv("FLASK_ENV"):
        app.jinja_env.auto_reload = True
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        extra_files=[
            "./static/stylesheets/style.css"
        ]

    app.run(
        host='0.0.0.0',
        port=8080,
        extra_files=extra_files,
        debug=True
    )
