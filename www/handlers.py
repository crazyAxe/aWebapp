#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from models import User, Blog, Comment
import logging;logging.basicConfig(level=logging.INFO)
from web_frame import get, post
import re
import time
from aiohttp import web
from models import User, Blog, Comments, find_all, next_id
from configs import configs
import hashlib
from apis import APIValueError, APIResourceError, APIError, APINotFoundError
import json

_RE_EMAIL = re.compile(r'^[a-z0-9\.\_\-]+\@[a-z0-9\-\_]+\.([a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'[0-9a-f]{40}$')

_COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def user2cookie(user, max_age):
    expires = str(max_age + int(time.time()))
    s = '%s-%s-%s-%s' % (user, user.password, expires, _COOKIE_NAME)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


def cookie2user(cookie_str):
    if not cookie_str:
        return None

    try:
        cookie = cookie_str.split('-')
        if len(cookie) != 3:
            return None
        uid, expires, sha1 = cookie
        if t < int(time.time):
            logging.info('invalid cookie.')
            return None
        user = yield from User.findall(uid)
        if not len(user):
            return None
        s = '%s-%s-%s-%s' % (uid, user.password, expires, _COOKIE_KEY)
        sha = hashlib.sha1(s.encode('utf-8')).hexdigest()
        if sha != sha1:
            logging.info('invalid sha1')
            return None
        user.password = '******'
        return
    except Exception as e:
        logging.exception(e)
        return None

@post('/api/user')
def api_regist_user(*, email, name, password):
    if not name or not name.strip():
        raise APIValueError('name')
    if not password:
        raise APIValueError('password')
    if not email:
        raise APIError('email')
    users = yield from User.findall('email', [email])
    if len(users) > 0:
        raise APIError('register error.', 'email', 'Email is in use')
    uid = next_id()
    sha_passwd = '%s:%s' % (uid, password)
    user = User(id=uid, name=name.strip(), email=email, password=hashlib.sha1(sha_passwd.encode('utf-8')).hexdigest(),
                image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    yield from user.save()
    r = web.Response()
    r.set_cookie(_COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type = 'application/json;charset=utf8'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


# -------------------------------用户管理--------------------------------


@get('/show_all_users')
def show_all_user(requset):
    users = yield from User.findAll()
    logging.info('index ...')
    return {
        'template': 'test.html',
        'users': users
    }


@get('/api/users')
def api_get_users(request):
    users = yield from User.findAll(orderBy='create_at desc')
    logging.info('user = %s and type = %s' % (users, type(users)))
    for u in users:
        u.password = '******'
    return dict(users=users)

