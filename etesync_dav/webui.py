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

from flask import Flask, render_template, redirect, url_for, request, session, Blueprint
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

import etesync as api
from etesync_dav.config import ETESYNC_URL
from etesync_dav.manage import Manager
from etesync_dav.mac_helpers import generate_cert, macos_trust_cert, needs_ssl, has_ssl
from .radicale.etesync_cache import EteSyncCache, etesync_for_user

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
    users = map(lambda x: (x, manager.get(x)), manager.list())
    return render_template('index.html', users=users, remove_user_form=remove_user_form, osx_ssl_warning=needs_ssl())


@app.route('/user/<string:user>')
@login_required
def user_index(user):
    with etesync_for_user(user) as (etesync, _):
        etesync.sync_journal_list()
        journals = etesync.list()
    collections = {}
    for journal in journals:
        collection = journal.collection
        collections[collection.TYPE] = collections.get(collection.TYPE, [])
        collections[collection.TYPE].append(collection)

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
            api.Authenticator(ETESYNC_URL).get_auth_token(form.username.data, form.login_password.data)
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


@app.route('/certgen/', methods=['GET', 'POST'])
@login_required
def certgen():
    if request.method == 'GET':
        return redirect(url_for('account_list'))

    form = FlaskForm(request.form)
    if form.validate_on_submit():
        generate_cert()
        macos_trust_cert()

        # FIXME: hack to kill server after generation.
        from threading import Timer

        def shutdown():
            sys.exit(0)

        thread = Timer(0.5, shutdown)
        thread.start()

        return render_template('shutdown_success.html')

    return redirect(url_for('account_list'))


@app.route('/add/', methods=['GET', 'POST'])
def add_user():
    if not logged_in() and len(list(manager.list())) > 0:
        return redirect(url_for('login'))

    errors = None
    form = AddUserForm(request.form)
    if form.validate_on_submit():
        try:
            manager.add(form.username.data, form.login_password.data, form.encryption_password.data)
            return redirect(url_for('account_list'))
        except Exception as e:
            errors = str(e)
    else:
        errors = form.errors

    return render_template('add_user.html', form=form, errors=errors)


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
    login_password = PasswordField('Account Password', validators=[DataRequired()])


class AddUserForm(LoginForm):
    encryption_password = PasswordField('Encryption Password', validators=[DataRequired()])


def run(debug=False):
    app.run(debug=debug, host=ETESYNC_LISTEN_ADDRESS, port=PORT)
