import json
import os
import base64

from flask import Flask, request, g, redirect, url_for
from oauthlib.oauth2 import WebApplicationClient
from oauthlib.common import add_params_to_uri

import requests

GOOGLE_CLIENT_ID = os.environ.get('OAUTH2_CLIENT_ID', None)
GOOGLE_CLIENT_SECRET = os.environ.get('OAUTH2_CLIENT_SECRET', None)
GOOGLE_AUTHORIZATION_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_ENDPOINT = 'https://openidconnect.googleapis.com/v1/userinfo'

PUBLIC_URL = os.environ.get('PUBLIC_URL', None)

client = WebApplicationClient(GOOGLE_CLIENT_ID)
app = Flask(__name__)


@app.route('/oauth2')
def login():
    print('received login request')
    redirect_url = PUBLIC_URL

    state = request.args.get('state')
    if not state:
        return 'empty state', 400

    request_uri = client.prepare_request_uri(
        GOOGLE_AUTHORIZATION_ENDPOINT,
        redirect_uri=redirect_url,
        scope=['openid', 'email', 'profile'],
        state=state
    )

    print('redirecting to ' + request_uri +
          ' with redirect_url ' + redirect_url)
    return redirect(request_uri)


@app.route('/oauth2/callback')
def callback():
    request_url = request.url.replace('http://', 'https://')
    request_base_url = request.base_url.replace('http://', 'https://')

    code = request.args.get('code')
    state = request.args.get('state')
    if not state:
        return 'empty state', 400

    decoded_state_json = json.loads(base64.b64decode(state))

    token_url, headers, body = client.prepare_token_request(
        GOOGLE_TOKEN_ENDPOINT,
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
    uri, headers, body = client.add_token(GOOGLE_USERINFO_ENDPOINT)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    if userinfo_response.json().get('email_verified'):
        unique_id = userinfo_response.json()['sub']
        users_email = userinfo_response.json()['email']
        picture = userinfo_response.json()['picture']
        users_name = userinfo_response.json()['given_name']
    else:
        return 'User email not available or not verified by Google.', 400

    print('successfully authenticated ' + users_email)
    redirect_url = decoded_state_json['prd']

    user = dict(id_=unique_id, name=users_name,
                email=users_email, profile_pic=picture)
    state = base64.b64encode(json.dumps(user).encode('utf-8'))

    # This is not secure. A production proxy should pass this information via a database
    # or another secure mechanism. This is only for demo purposes.
    params = [('state', state)]
    redirect_url_with_state = add_params_to_uri(redirect_url, params)
    return redirect(redirect_url_with_state)


if __name__ == '__main__':
    extra_files = []
    if 'development' == os.getenv('FLASK_ENV'):
        app.jinja_env.auto_reload = True
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        extra_files = [
            './static/stylesheets/style.css'
        ]

    app.run(
        host='0.0.0.0',
        port=8080,
        extra_files=extra_files,
        debug=True
    )
