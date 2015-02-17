# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from itsdangerous import BadData
from relengapi import p
from relengapi.blueprints.tokenauth.tables import Token


class FakeSerializer(object):

    @staticmethod
    def prm(id):
        return FakeSerializer.dumps(
            {"iss": "ra2", "jti": "t%d" % id, "typ": "prm"})

    @staticmethod
    def tmp(nbf, exp, prm, mta):
        return FakeSerializer.dumps(
            {"iss": "ra2", "typ": "tmp", 'nbf': nbf,
             "exp": exp, "prm": prm, "mta": mta})

    @staticmethod
    def usr(id):
        return FakeSerializer.dumps(
            {"iss": "ra2", "jti": "t%d" % id, "typ": "usr"})

    @staticmethod
    def dumps(data):
        return 'FK:' + json.dumps(data,
                                  separators=(',', ':'),
                                  sort_keys=True)

    @staticmethod
    def loads(data):
        if data[:3] != 'FK:':
            raise BadData('Not a fake token')
        else:
            return json.loads(data[3:])

# sample tokens


prm_json = {
    'id': 1,
    'typ': 'prm',
    'description': 'Zig only',
    'permissions': ['test_tokenauth.zig'],
}

usr_json = {
    'id': 2,
    'typ': 'usr',
    'user': 'me@me.com',
    'description': 'User Zig',
    'permissions': ['test_tokenauth.zig'],
}


def insert_prm(app):
    session = app.db.session('relengapi')
    t = Token(
        id=1,
        typ='prm',
        permissions=[p.test_tokenauth.zig],
        description="Zig only")
    session.add(t)
    session.commit()


def insert_usr(app):
    session = app.db.session('relengapi')
    t = Token(
        id=2,
        typ='usr',
        user='me@me.com',
        permissions=[p.test_tokenauth.zig],
        description="User Zig")
    session.add(t)
    session.commit()


def insert_all(app):
    insert_prm(app)
    insert_usr(app)
