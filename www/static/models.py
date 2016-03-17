#!/usr/bin/env python3
# -*- coding:utf8 -*-

import uuid
import time
from www.static.orm import Model, StringField, BooleanField, TextField, FloatField

def next_id():
    return '%s015d%s' % (time.time()*1000, uuid.uuid4().hex)

class User(Model):
    __table__ = 'user'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    name = StringField(ddl='varchar(50)')
    password = StringField(ddl='varchar(50)')
    admin = BooleanField()
    image = StringField(ddl='varchar(500)')
    create_at = FloatField(default=time.time)

class Blog(Model):
    __table__ = 'blog'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(50)')
    name = StringField(ddl='varchar(50)')
    content = TextField()
    summary = StringField(ddl='varchar(500)')
    create_at = FloatField(default=time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(50)')
    content = TextField()
    create_at = FloatField(default=time.time)




