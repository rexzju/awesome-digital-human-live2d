# -*- coding: utf-8 -*-
'''
@File    :   __init__.py
@Author  :   一力辉 
'''

from .configParser import *
from .logger import *
from .registry import *
from .audio import *
from .func import *
from .streamParser import *

# https://www.cnblogs.com/nanshaobit/p/16060370.html
import httpx
RETRIES = 3
# 设置适当的超时时间（30秒）而不是 None
asyncTransport = httpx.AsyncHTTPTransport(retries=RETRIES, verify=False)
httpxAsyncClient = httpx.AsyncClient(timeout=30.0, transport=asyncTransport)
syncTransport = httpx.HTTPTransport(retries=RETRIES, verify=False)
httpxSyncClient = httpx.Client(timeout=30.0, transport=syncTransport)