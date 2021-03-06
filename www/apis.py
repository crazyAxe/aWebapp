#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import logging
import inspect
import functools


class APIError(Exception):
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message


class APIValueError(APIError):
    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('invalid value', field, message)


class APIResourceNotFoundError(APIError):
    def __init__(self, field, message=''):
        super(APIResourceNotFoundError, self).__init__('value: not found', field, message)


class APIPermissionError(APIError):
    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('Permission forbidden.', 'permission', message)


class Page(object):
    def __init__(self, item_count, page_index=1, page_size=2):
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0  # 本页能显示的数量
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (self.page_index - 1)
            self.limit = self.page_size
        self.hasNext = (self.page_index < self.page_count)
        self.hasPrevious = (self.page_index > 1)

    def __str__(self):
        return 'item_count: %s ,page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % \
               (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)

    __repr__ = __str__




