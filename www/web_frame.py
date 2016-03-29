#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os
import inspect
import asyncio
import logging
logging.basicConfig(level=logging.INFO)
import functools

from aiohttp import web
from urllib import parse
from apis import APIError


# 关于decorator,可以参考Kaiming Wan 的blog：kaimingwan.com/post/python/pythonzhuang-shi-qi-ying-yong

def get(path):
    """
        define decorator @get('/path')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*para, **kw):
            return func(*para, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator


def post(path):
    """
        Define decorator @post('/path')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*para, **kw):
            return func(*para, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator


def get_required_kw_args(func):
    # 如果url处理函数需要传入关键字参数，并且默认为空，则取得这个参数

    args = []
    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


def get_named_kw_args(func):
    # 如果url处理函数需要传入关键字参数，则取得这个函数

    args = []
    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


def has_named_kw_args(func):
    # 判断是否有指定命名的关键字参数

    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


def has_var_kw_args(func):
    # 判断是否有关键字参数，Var_KEYWORD 对应**kw

    params = inspect.signature(func).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True


def has_request_args(func):
    # 判断是否有request参数，并且request参数必须在普通参数之后，及在*kw, **kw ,* 或者 *args 之后

    sig = inspect.signature(func)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD
                              and param.kind != inspect.Parameter.VAR_POSITIONAL):
            raise ValueError('request parameter must be the last named parameter in function: %s %s' %
                             (func.__name__, str(sig)))
    return found


class RequestHandler(object):
    def __init__(self, app, func):
        self._app = app
        self._func = func
        self._has_request_args = has_request_args(func)
        self._has_var_kw_args = has_var_kw_args(func)
        self._has_named_kw_args = has_named_kw_args(func)
        self._required_kw_args = get_required_kw_args(func)
        self._named_kw_args = get_named_kw_args(func)

    def __call__(self, request):
        kw = None
        # 创建kw用来保存参数
        # 确保有参数：
        if self._has_var_kw_args or self._has_named_kw_args or self._named_kw_args:
            # ----step1 POST/GET 方法下正确解析参数，包括位置参数与关键字参数

            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type. ')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = yield from request.json() # 如果请求json数据
                    if isinstance(params, dict):  # 参数如果不是dict类型，json body 报错
                        return web.HTTPBadRequest('JSON body must be a object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencode') or ct.startswith('multipart/form-data'):
                    params = yield from request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Tyoe: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]

        if kw is None:
            kw = dict(**request.match_info)
        else:
            # 当没有可变参数，有命名关键字参数时，将kw指向命名关键字参数:
            if not self._has_var_kw_args and self._has_named_kw_args:
                copy = dict()
                # remove all unnamed kw:
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # 检查命名关键字中的name是否和match_info中的重复:
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate name args in named args and var args: %s ' % k)
                kw[k] = kw[v]
        if self._has_request_args:
            kw['request'] = request
        if self._required_kw_args:
            for name in self._required_kw_args:
                if name not in kw.items():
                    return web.HTTPBadRequest('Miss arguments %s.' % name)
        logging.info('call with args : %s' % str(kw))
        try:
            r = yield from self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.date, message=e.message)


# 添加静态页面路径
def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s ==> %s' % ('/static/', path))


def add_route(app, fn):
    # add_route函数用来注册一个url处理函数
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('method @get or @post is not defined in %s' % str(fn))
    if not asyncio.iscoroutine(fn) and not inspect.isgeneratorfunction(fn):
        # 强制转换为协程
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s == > %s %s' % (method, path, fn.__name__,
                                                 ' ,'.join(inspect.signature(fn).parameters.keys())))
    # 正式注册为相应的url处理方法
    # 处理方法为RequestHandler的自省函数'__call__'
    app.router.add_route(method, path, RequestHandler(app, fn))


def add_routes(app, module_name):
    # 自动搜索传入module_name的module的url处理函数
    # python rfind()函数返回字符串最后一次出现的位子，如果没有则返回-1
    n = module_name.rfind('.')
    logging.info('n = %s', n)
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
        logging.info('globals = %s' % globals()['__name__'])
    else:
        mod = __import__(module_name[:n], globals(), locals())
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)



