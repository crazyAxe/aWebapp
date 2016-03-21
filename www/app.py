#/usr/bin/env python3
# -*- coding:utf8 -*-

import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

# def index(request):
#     return web.Response(body=b'<h1>Awesome</h1>')
#
# @asyncio.coroutine
# def init(loop):
#     app = web.Application(loop=loop)
#     app.router.add_route('GET', '/', index)
#     srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
#     logging.info('server started at http:/127.0.0.1:9000...')
#     return srv
#
# loop = asyncio.get_event_loop()
# loop.run_until_complete(init(loop))
# loop.run_forever()

import os
from jinja2 import Environment, FileSystemLoader
from aiohttp import web
from handler import cookie2user, COOKIE_NAME

def init_jinja2(app, **kw):
    logging.info('Init jinja2 ...')
    options = dict(
        autoescape=kw.get('autoescpte', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template')
    logging.info('set jinja2 template path:%s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filter is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env

# --------------------------------------------middleware config---------------------------------------------


@asyncio.coroutine
def log_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        logging.info('request: %s, %s' % (request.method, request.path))
        return (yield from handler(request))
    return logger


@asyncio.coroutine
def data_factory(app, handler):
    @asyncio.coroutine
    def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = yield from request.json()
                logging.info('request json: %s ' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-rulencode'):
                request.__data__ = yield from request.post()
                logging.info('request form: %s ' % str(request.__data__))
        return (yield from handler(request))
    return parse_data


@asyncio.coroutine
def auth_factory(app, handler):
    @asyncio.coroutine
    def auth(request):
        logging.info('check user : %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_usr = request.cookies.get(COOKIE_NAME)
        if cookie_usr:
            user = yield from cookie2user(cookie_usr)
            logging.info('current user : ' % user.email)
            request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/signin')
        return (yield from handler(request))
    return auth_factory


@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info('Response handler...')
        r = yield from handler(request)
        logging.info('Response: %s ' % str(r))
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                reps = web.Response(json.dumps(r, ensure_ascii=False, default=lambda o : o.__dict__).encode('utf-8'))
                reps.content_type = 'application/json;charset=utf-8'
            else:
                r['__user__'] = request.__user__
                resp = web.Response(body=app['__templating__'].getTemplate(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            s, m = r
            if isinstance(s, int) and s >=100 and s < 600:
                return web.Response(status=s, text=m)
            resp = web.Response(body=str(r).encode('utf-8'))
            resp.content_type = 'text/plain;charset=utf-8'
            return resp
    return response
