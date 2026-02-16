#!/usr/bin/env python
import sys
import os
import json
import traceback
from multiprocessing import Process
from os import environ
from wsgiref.simple_server import make_server, WSGIRequestHandler
import logging

from KBDatalakeDashboard.KBDatalakeDashboardImpl import KBDatalakeDashboard


class MethodContext(object):
    def __init__(self, logger):
        self.logger = logger
        self.provenance = []


class JSONObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, frozenset):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class JSONRPCServiceCustom(object):
    def __init__(self, impl_instance=None, config=None):
        if impl_instance is None:
            raise ValueError('instantiation failed, impl_instance argument was None')
        self.impl_instance = impl_instance
        self.config = config
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s: %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.info("KBDatalakeDashboard server started")

    def call(self, ctx, method, params):
        if method == 'KBDatalakeDashboard2.run_genome_datalake_dashboard':
            return self.impl_instance.run_genome_datalake_dashboard(ctx, params)
        elif method == 'KBDatalakeDashboard2.status':
            return self.impl_instance.status(ctx)
        else:
            raise ValueError('Unknown method: ' + method)


def get_config_file():
    return environ.get('KB_DEPLOYMENT_CONFIG', 'deploy.cfg')


def get_config():
    cfg = {}
    config_file = get_config_file()
    if config_file is not None:
        with open(config_file) as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    cfg[key] = value
    return cfg


class JSONRPCServer(object):
    def __init__(self):
        config = get_config()
        self.impl_instance = KBDatalakeDashboard(config)
        self.service = JSONRPCServiceCustom(self.impl_instance, config)

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'OPTIONS':
            headers = [
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Headers', 'authorization, content-type'),
                ('Access-Control-Allow-Methods', 'POST'),
                ('Content-Type', 'application/json'),
            ]
            start_response('200 OK', headers)
            return [b'']

        try:
            body_size = int(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            body_size = 0

        if body_size == 0:
            start_response('200 OK', [('Content-Type', 'application/json')])
            return [json.dumps({'version': '1.1', 'result': [{}]}).encode('utf-8')]

        request_body = environ['wsgi.input'].read(body_size)
        try:
            req = json.loads(request_body.decode('utf-8'))
        except ValueError as e:
            err_msg = 'Error parsing request JSON: ' + str(e)
            start_response('400 Bad Request', [('Content-Type', 'application/json')])
            return [json.dumps({'error': err_msg}).encode('utf-8')]

        ctx = MethodContext(self.service.logger)

        try:
            result = self.service.call(ctx, req['method'], req['params'][0])
            output = {
                'version': '1.1',
                'result': result
            }
        except Exception as e:
            self.service.logger.exception('Error executing method')
            output = {
                'version': '1.1',
                'error': {
                    'name': str(type(e).__name__),
                    'message': str(e),
                    'error': traceback.format_exc()
                }
            }

        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*')
        ])
        return [json.dumps(output, cls=JSONObjectEncoder).encode('utf-8')]


application = JSONRPCServer()


if __name__ == '__main__':
    httpd = make_server('', 5000, application)
    print('Server starting on port 5000...')
    httpd.serve_forever()
