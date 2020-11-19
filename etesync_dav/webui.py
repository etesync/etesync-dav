# Copyright © 2017 Tom Hacohen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import os
from functools import wraps
from urllib.parse import urljoin

from flask import Flask, render_template, redirect, url_for, request, session
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField
from wtforms.fields.html5 import URLField
from wtforms.validators import Optional, DataRequired, url

import etesync as api
from etesync_dav.manage import Manager
from etesync_dav.mac_helpers import generate_cert, trust_cert, needs_ssl, has_ssl
from .radicale.etesync_cache import etesync_for_user
from etesync_dav.local_cache import Etebase
from etesync_dav.config import LEGACY_ETESYNC_URL, ETESYNC_URL

manager = Manager()


PORT = 37359
BASE_URL = os.environ.get('ETESYNC_DAV_URL', '/')
ETESYNC_LISTEN_ADDRESS = os.environ.get('ETESYNC_LISTEN_ADDRESS', '127.0.0.1')


def prefix_route(route_function, prefix='', mask='{0}{1}'):
    '''
      Defines a new route function with a prefix.
      The mask argument is a `format string` formatted with, in that order:
        prefix, route
    '''
    def newroute(route, *args, **kwargs):
        '''New function to prefix the route'''
        return route_function(mask.format(prefix, route), *args, **kwargs)
    return newroute


# Special handling from frozen apps
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'etesync_dav', 'templates')
    app = Flask(__name__, template_folder=template_folder)
else:
    app = Flask(__name__)

app.route = prefix_route(app.route, '/.web')

app.secret_key = os.urandom(32)
CSRFProtect(app)


@app.context_processor
def inject_user():
    import etesync_dav
    return dict(version=etesync_dav.__version__)


def login_user(username):
    session['username'] = username


def logout_user():
    session.pop('username', None)


def logged_in():
    return 'username' in session


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not logged_in():
            # If we don't have any users, redirect to adding a user.
            if len(list(manager.list())) > 0:
                return redirect(url_for('login'))
            else:
                return redirect(url_for('add_user'))
        return func(*args, **kwargs)
    return decorated_view


@app.route('/')
@login_required
def account_list():
    remove_user_form = UsernameForm(request.form)
    username = session['username']
    password = manager.get(username)
    server_url_example = "{}://localhost:37358/{}/".format("https" if has_ssl() else "http", username)
    return render_template('index.html', username=username, password=password, remove_user_form=remove_user_form,
                           osx_ssl_warning=needs_ssl(), server_url_example=server_url_example)


@app.route('/user/<string:user>')
@login_required
def user_index(user):
    if session['username'] != user:
        return redirect(url_for('user_index', user=session['username']))
    type_name_mapper = {
        "etebase.vevent": "Calendars",
        "etebase.vtodo": "Tasks",
        "etebase.vcard": "Address Books",
    }
    collections = {}
    with etesync_for_user(user) as (etesync, _):
        if isinstance(etesync, Etebase):
            etesync.sync_collection_list()
            for col in etesync.list():
                col_type = type_name_mapper.get(col.col_type, None)
                if col_type is not None:
                    collections[col_type] = collections.get(col_type, [])
                    collections[col_type].append({"name": col.meta["name"], "uid": col.uid})
        else:
            etesync.sync_journal_list()
            journals = etesync.list()
            for journal in journals:
                collection = journal.collection
                collections[collection.TYPE] = collections.get(collection.TYPE, [])
                collections[collection.TYPE].append({"name": collection.display_name, "uid": journal.uid})

    return render_template(
            'user_index.html', BASE_URL=urljoin(BASE_URL, "{}/".format(user)), collections=collections)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if logged_in():
        return redirect(url_for('account_list'))

    errors = None
    form = LoginForm(request.form)
    if form.validate_on_submit():
        try:
            manager.refresh_token(form.username.data, form.login_password.data)
            login_user(form.username.data)
            return redirect(url_for('account_list'))
        except Exception as e:
            errors = str(e)
    else:
        errors = form.errors

    return render_template('login.html', form=form, errors=errors)


@app.route('/logout/', methods=['POST'])
@login_required
def logout():
    form = FlaskForm(request.form)
    if form.validate_on_submit():
        logout_user()

    return redirect(url_for('login'))


# FIXME: hack to kill server after generation.
def shutdown_response():
    from threading import Timer

    def shutdown():
        os._exit(0)

    thread = Timer(0.5, shutdown)
    thread.start()

    return redirect(url_for('shutdown_success'))


@app.route('/shutdown/', methods=['POST'])
@login_required
def shutdown():
    form = FlaskForm(request.form)
    if form.validate_on_submit():
        return shutdown_response()

    return redirect(url_for('login'))


@app.route('/shutdown/success/', methods=['GET'])
@login_required
def shutdown_success():
    return render_template('shutdown_success.html')


@app.route('/certgen/', methods=['GET', 'POST'])
@login_required
def certgen():
    if request.method == 'GET':
        return redirect(url_for('account_list'))

    form = FlaskForm(request.form)
    if form.validate_on_submit():
        generate_cert()
        trust_cert()

        return shutdown_response()

    return redirect(url_for('account_list'))


@app.route('/add/', methods=['GET', 'POST'])
def add_user():
    errors = None
    form = AddUserForm(request.form)
    if form.validate_on_submit():
        try:
            server_url = form.server_url.data
            server_url = ETESYNC_URL if server_url == "" else server_url
            manager.add_etebase(form.username.data, form.login_password.data, server_url)
            return redirect(url_for('account_list'))
        except Exception as e:
            errors = str(e)
    else:
        errors = form.errors

    return render_template('add_user.html', form=form, errors=errors)


@app.route('/add_legacy/', methods=['GET', 'POST'])
def add_user_legacy():
    errors = None
    form = AddUserLegacyForm(request.form)
    if form.validate_on_submit():
        try:
            server_url = form.server_url.data
            server_url = LEGACY_ETESYNC_URL if server_url == "" else server_url
            manager.add(form.username.data, form.login_password.data, form.encryption_password.data, server_url)
            return redirect(url_for('account_list'))
        except api.exceptions.IntegrityException:
            errors = 'Wrong encryption password (failed to decrypt data)'
        except Exception as e:
            errors = str(e)
    else:
        errors = form.errors

    return render_template('add_user_legacy.html', form=form, errors=errors)


@app.route('/remove_user/', methods=['GET', 'POST'])
@login_required
def remove_user():
    form = UsernameForm(request.form)
    if form.validate_on_submit():
        manager.delete(form.username.data)

    return redirect(url_for('account_list'))


class UsernameForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])


class LoginForm(UsernameForm):
    server_url = URLField('Server URL (Leave Empty for Default)', validators=[Optional(), url(require_tld=False)])
    login_password = PasswordField('Account Password', validators=[DataRequired()])


class AddUserForm(LoginForm):
    pass


class AddUserLegacyForm(LoginForm):
    encryption_password = PasswordField('Encryption Password', validators=[DataRequired()])


def run(debug=False):
    app.run(debug=debug, host=ETESYNC_LISTEN_ADDRESS, port=PORT)
