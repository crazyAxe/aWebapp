#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from models import User, Blog, Comment, next_id
import logging;logging.basicConfig(level=logging.DEBUG)
from web_frame import get, post
import re
from apis import APIValueError, APIResourceNotFoundError, APIError
import configs.session.secret
import hashlib
from aiohttp import web
import time
import json
import asyncio

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'[0-9a-f]{40}$')

_COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def user2cookie(user, max_age):
    expires = str(int(time.time()) + max_age)
    s = '%s-%s-%s-%s' % (user, user.password, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


@asyncio.coroutine
def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = yield from User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.password, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-9')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.password = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return e


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

# -----------------------------------------------------


@post('/api/users')
def api_register_user(*, email, name, password):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not password or not _RE_SHA1.match(password):
        raise APIValueError('password')
    users = yield from User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register failed!', 'email', 'Email is already in use')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, password)
    admin = False
    if email == 'admin@163.com':
        admin = True

    user = User(id=uid, name=name.strip(), password=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
                image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest(),
                admin=admin)
    yield from user.save()
    logging.info('save user ok.')
    # 构建返回信息
    r = web.Response()
    r.set_cookie(_COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    # 把要返回的实例的密码改成‘******’,这样数据库中的密码是正确的，并保证真实的密码不会因返回而泄露
    user.password = '******'
    r.content_type = 'application/json;charset:utf-8'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r
