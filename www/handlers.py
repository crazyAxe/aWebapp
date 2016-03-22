#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from models import User, Blog, Comment
import logging;logging.basicConfig(level=logging.INFO)
from web_frame import get, post


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

