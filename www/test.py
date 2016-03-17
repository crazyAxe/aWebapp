#!/usr/bin/env python3
# -*- coding:utf8 -*-

import  asyncio
import orm
from models import User, Blog, Comment

def test(loop):
    yield from orm.create_pool(loop=loop, user='root', password='password', db='myblog')
    u = User(name='Test', password='123456', email='test@example.com', image='about:blank')

    yield from u.save

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()
