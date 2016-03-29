#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from models import User, Blog, Comment, next_id
import logging;logging.basicConfig(level=logging.DEBUG)
import re
from apis import APIValueError, APIResourceNotFoundError, APIError, Page, APIPermissionError
from config import configs
import hashlib
from aiohttp import web
import time
import json
import asyncio
from models import User, Blog, Comment
import logging;logging.basicConfig(level=logging.INFO)
from web_frame import get, post
import markdown2

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'[0-9a-f]{40}$')

_COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % (s.replace('&', '&amp;').replace('<', '&lt').replace('>', '&gt')),
                filter(lambda s: s.split() != '', text.split('\n')))
    return ''.join(lines)


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


@get('/')
def index(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    page = Page(num, page_index)
    if num == 0:
        blogs = []
    else:
        blogs = yield from Blog.findAll(orderBy='create_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'blogs.html',
        'blogs': blogs,
        'page': page
    }


@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }

# 登陆页面


@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }


@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    # 清理掉cookie得用户信息数据
    r.set_cookie(_COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out')
    return


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


@post('/api/authenticate')
def authenticate(*, email, password):
    if not email:
        raise APIValueError('email', 'invalid email')
    if not password:
        raise APIValueError('password', 'invalid password')
    users = yield from User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'email not exist')
    user = users[0]
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(password.encode('utf-8'))
    if sha1.hexdigest() != user.password:
        raise APIValueError('password', 'invalid password')
    r = web.Response()
    r.set_cookie(_COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return

# -------------------------------评论管理 --------------------------------


@get('/manage/')
def manage():
    return 'redirect: /manage/comments'


@get('/manage/comments')
def manage_comments(*, page='1'):
    # 查看所有评论
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }


@get('/api/comments')
def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Comment.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, comments=())
    comments = yield from Comment.findAll(orderBy='create_at desc', limit=(p.offset, p.limit))
    return dict(page=p, comments=comments)


@post('/api/blogs/{id}/comments')
def api_create_comments(id, request, *, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('content')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(id=next_id(), user_id=user.id, user_name=user.name, image=user.image, content=content.strip())
    yield from comment.save()
    return comment


@post('/api/comments/{id}/delete')
def api_delete_comment(id, request):
    logging.info(id)
    check_admin(request)
    comment = yield from Comment.find(id)
    if comment is None:
        raise APIResourceNotFoundError('comment')
    yield from comment.remove()
    return dict(id=id)


# -------------------------------用户管理--------------------------------


@get('/show_all_users')
def show_all_user(request):
    users = yield from User.findAll()
    logging.info('index ...')
    return {
        '__template__': 'test.html',
        'users': users
    }


@get('/api/users')
def api_get_users(request):
    users = yield from User.findAll(orderBy='create_at desc')
    logging.info('user = %s and type = %s' % (users, type(users)))
    for u in users:
        u.password = '******'
    return dict(users=users)


@get('/manage/users')
def manage_users(*, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': page
    }


# --------------------------------博客管理--------------------------------------


@get('/manage/blogs/create')
def manage_create_blog():
    # 写博客
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }


@get('/manage/blogs')
def manage_blogs(*, page='1'):
    # 博客管理
    return {
        '__template__': 'manage_blogs.html',
        'page_index': page
    }


@get('/api/blogs')
def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    page = Page(num, page_index)
    if num == 0:
        return dict(page=page, blogs=())
    blogs = yield from Blog.findAll(orderBy='create_at desc', limit=(page.offset, page.limit))
    return dict(blogs=blogs, page=page)


@post('/api/blogs')
def api_create_blogs(request, *, name, summary, content):
    check_admin(request)
    if name is None:
        raise APIValueError('name', 'name can\'t be empty!')
    if summary is None:
        raise APIValueError('summary', 'summary can not be empty')
    if content is None:
        raise APIValueError('content', 'content can not be empty')
    blog = yield from Blog(user_id=request.__user__.id, user_name=request.__user__.name,
                           user_image=request.__user__.image, name=name, summary=summary, content=content)
    yield from blog.save()
    return blog


@get('/blog/{id}')
def get_blog(id):
    blog = yield from Blog.find(id)
    # if blog is None:
    #     raise APIResourceNotFoundError('blog', 'blog not found')
    comments = yield from Comment.findAll('blog_id=?', [id], orderBy='create_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }


@get('/api/blogs/{id}')
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog


@post('/api/blogs/{id}/delete')
def api_delete_blog(id, request):
    logging.info('delete a blog %s', id)
    check_admin(request)
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('blog not found')
    yield from blog.remove()
    raise dict(id=id)


# 修改博客
@post('/api/blogs/modify')
def api_modify_blog(request, *, id, name, summary, content):
    logging.info('修改博客的id为: %s', id)
    if not name or not name.strip():
        raise APIValueError('name', ' name can not be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary can not be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content can not be empty')
    blog = yield from Blog.find(id)
    blog.name = name
    blog.summary = summary
    blog.content = content
    yield from blog.update()
    return blog


@get('/manage/blogs/manage/{id}')
def manage_modify_blog(id):
    return {
        '__template__': 'manage_blog_modify.html',
        'id': id,
        'action': '/api/blogs/modify'
    }