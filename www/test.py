#!/usr/bin/env python3
# -*- coding:utf8 -*-

import  asyncio
import orm
from models import User, Blog, Comment


@asyncio.coroutine
def test_save(loop):
    yield from orm.create_pool(loop=loop, user='root', password='password', db='myblog')
    u = User(name='Test', password='123456', email='test@example.com', image='about:blank')

    yield from u.save()


@asyncio.coroutine
def test_select(loop):
    yield from orm.create_pool(loop=loop, user='root', password='password', db='myblog')
    rs = yield from User.findAll(email='test@example.com')
    for i in range(len(rs)):
        print(rs[i])

@asyncio.coroutine
def test_update(loop):
    yield from orm.create_pool(loop=loop, user='root', password='password', db='myblog')
    u = User(name='Test')


loop = asyncio.get_event_loop()
loop.run_until_complete(test_select(loop))
# __loop = orm.__loop
# __loop.close()
# loop.run_until_complete(__loop.close())
loop.close()
