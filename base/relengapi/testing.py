# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import inspect
from flask import g
from flask import json
import relengapi.app
from nose.tools import make_decorator


class TestContext(object):

    _known_options = set([
        'databases',
        'reuse_app',
        'app_setup',
        'db_setup',
        'db_teardown',
        'config',
        'actions',
    ])

    def __init__(self, **options):
        self._validate(options)
        self.options = options
        self._app = None

    def specialize(self, **options):
        new_options = self.options.copy()
        new_options.update(options)
        return TestContext(**new_options)

    def _validate(self, options):
        unknown = set(options) - self._known_options
        if unknown:
            raise ValueError("unknown options %s" % (', '.join(unknown)))
        # verify that all actions exist
        if options.get('actions'):
            for action in options['actions']:
                assert action.exists()

    def _make_app(self):
        if self.options.get('reuse_app') and self._app:
            return self._app
        config = self.options.get('config', {}).copy()
        config['TESTING'] = True
        config['SECRET_KEY'] = 'test'
        config['SQLALCHEMY_DATABASE_URIS'] = uris = {}
        dbnames = self.options.get('databases', [])
        for dbname in dbnames:
            uris[dbname] = 'sqlite://'
        app = relengapi.app.create_app(test_config=config)

        # set up actions
        if self.options.get('actions') is not None:
            @app.before_request
            def set_actions():
                g.identity.provides.update(set(self.options['actions']))

        # set up the requested DBs
        for dbname in dbnames:
            meta = app.db.metadata[dbname]
            engine = app.db.engine(dbname)
            meta.create_all(bind=engine)
        self._app = app
        if 'app_setup' in self.options:
            self.options['app_setup'](app)
        return app

    def __call__(self, func):
        arginfo = inspect.getargspec(func)
        args = set((arginfo.args if arginfo.args else []) +
                   (arginfo.keywords if arginfo.keywords else []))

        @make_decorator(func)
        def wrap(**kwargs):
            def post_json(path, data):
                return kwargs['client'].post(
                        path, data=json.dumps(data),
                        headers=[('Content-Type', 'application/json')])
            app = self._make_app()
            if 'app' in args:
                kwargs['app'] = app
            if 'client' in args:
                kwargs['client'] = app.test_client()
                kwargs['client'].post_json = post_json
            if 'db_setup' in self.options:
                self.options['db_setup'](app)
            try:
                func(**kwargs)
            finally:
                if 'db_teardown' in self.options:
                    self.options['db_teardown'](app)
        return wrap
