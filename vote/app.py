from flask import Flask, render_template, request, make_response, jsonify, g, redirect, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
    UserMixin
)

from oauthlib.common import add_params_to_uri
import requests
from redis import Redis, RedisError


import os
import base64
import socket
import random
import json
import collections


PUBLIC_URL = os.environ.get('PUBLIC_URL', None)
OAUTH2_PROXY_URL = os.environ.get('OAUTH2_PROXY_URL', None)

hostname = socket.gethostname()
redis = Redis(host='redis', db=0)
users = dict()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, id_, name, email, profile_pic):
        self.id = id_
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

def getOptions():
    option_a = 'Tacos'
    option_b = 'Burritos'
    return option_a, option_b

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

@app.route('/', methods=['POST','GET'])
def index():
    if current_user.is_authenticated:
        option_a, option_b = getOptions()

        try:
            votesA = int(redis.get(option_a) or 0) 
            votesB = int(redis.get(option_b) or 0)
        except RedisError:
            votesA = '<i>cannot connect to Redis, counter disabled</i>'
            votesB = '<i>cannot connect to Redis, counter disabled</i>'

        if request.method == 'POST':
            try:
                vote = request.form['vote']
                if vote == 'a':
                    votesA = redis.incr(option_a)
                else:
                    votesB = redis.incr(option_b)
            except Exception as e:
                print(e)
                votesA = '<i>An error occured</i>'
                votesB = '<i>An error occured</i>'

        with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'r') as fp:
            namespace = fp.read()

        resp = make_response(render_template(
            'index.html',
            option_a=option_a,
            option_b=option_b,
            hostname=hostname,
            namespace=namespace,
            username=current_user.name,
            votes_a=votesA,
            votes_b=votesB,
        ))
        return resp
    else:
        return make_response(render_template('login.html'))

@app.route('/oauth2')
def login():
    state = base64.b64encode(json.dumps({'prd': PUBLIC_URL}).encode('utf-8'))
    params = [('state', state)]
    redirect_url = add_params_to_uri(OAUTH2_PROXY_URL, params)
    print('redirecting request to proxy at ' + redirect_url)
    return redirect(redirect_url)

@app.route('/oauth2/callback')
def callback():
    print('received request from proxy')
    state = request.args.get('state')
    if not state:
        return 'empty state', 400

    decoded_state_json = json.loads(base64.b64decode(state))
    print(decoded_state_json)

    user = User(id_=decoded_state_json['id_'], name=decoded_state_json['name'], email=decoded_state_json['email'], profile_pic=decoded_state_json['profile_pic'])
    if decoded_state_json['id_'] not in users:
        users[decoded_state_json['id_']] = user

    login_user(user)
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    extra_files = []
    if 'development' == os.getenv('FLASK_ENV'):
        app.jinja_env.auto_reload = True
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        extra_files=[
            './static/stylesheets/style.css'
        ]

    app.run(
        host='0.0.0.0',
        port=8080,
        extra_files=extra_files,
        debug=True
    )
