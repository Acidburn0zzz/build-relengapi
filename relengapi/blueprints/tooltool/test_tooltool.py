# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import hashlib
import json
import mock
import moto
import time
import urlparse

from contextlib import contextmanager
from nose.tools import eq_
from relengapi.blueprints.tooltool import tables
from relengapi.lib.testing.context import TestContext

cfg = {
    'AWS': {
        'access_key_id': 'aa',
        'secret_access_key': 'ss',
    },
    'TOOLTOOL_REGION': 'us-east-1',
    'TOOLTOOL_BUCKET': 'tt-bucket',
}
test_context = TestContext(config=cfg, databases=['tooltool'])

ONE = '1\n'
ONE_HASH = hashlib.sha512(ONE).hexdigest()
TWO = '22\n'
TWO_HASH = hashlib.sha512(TWO).hexdigest()

NOW = 1425592922


def mkbatch():
    return {
        'author': 'me',
        'message': 'a batch',
        'files': {
            'one': {'algorithm': 'sha512', 'size': len(ONE), 'digest': ONE_HASH},
        },
    }


def upload_batch(client, batch):
    return client.put('/tooltool/batch', data=json.dumps(batch),
                      headers={'Content-Type': 'application/json'})


def add_file_to_db(app, content, regions=['us-east-1']):
    with app.app_context():
        file_row = tables.File(size=len(content),
                               sha512=hashlib.sha512(content).hexdigest())
        app.db.session('tooltool').add(file_row)
        app.db.session('tooltool').commit()
        # TODO: when the file has no instances, we should get a put_url
        for region in regions:
            instance_row = tables.FileInstance(file_id=file_row.id, region=region)
            app.db.session('tooltool').add(instance_row)
        app.db.session('tooltool').commit()

        return file_row.id


@contextmanager
def set_time(now=NOW):
    with mock.patch('time.time') as fake:
        fake.return_value = now
        yield


def assert_signed_302(resp, digest, method='GET', region=None,
                      expires_in=60, bucket=None):
    eq_(resp.status_code, 302)
    url = resp.headers['Location']
    assert_signed_url(url, digest, method=method, region=region,
                      expires_in=expires_in, bucket=bucket)


def assert_signed_url(url, digest, method='GET', region=None,
                      expires_in=60, bucket=None):
    region = region or cfg['TOOLTOOL_REGION']
    bucket = bucket or cfg['TOOLTOOL_BUCKET']
    if region == 'us-east-1':
        host = '{}.s3.amazonaws.com'.format(bucket)
    else:
        host = '{}.s3-{}.amazonaws.com'.format(bucket, region)
    url = urlparse.urlparse(url)
    eq_(url.scheme, 'https')
    eq_(url.netloc, host)
    eq_(url.path, '/sha512/{}'.format(digest))
    query = urlparse.parse_qs(url.query)
    assert 'Signature' in query
    # sadly, headers are not represented in the URL
    eq_(query['AWSAccessKeyId'][0], 'aa')
    eq_(int(query['Expires'][0]), time.time() + expires_in)


@moto.mock_s3
@test_context
def test_upload_batch_empty_message(client):
    """A PUT to /batch with an empty message is rejected."""
    batch = mkbatch()
    batch['message'] = ''
    resp = upload_batch(client, batch)
    eq_(resp.status_code, 400)


@moto.mock_s3
@test_context
def test_upload_batch_empty_files(client):
    """A PUT to /batch with no files is rejected."""
    batch = mkbatch()
    batch['files'] = {}
    resp = upload_batch(client, batch)
    eq_(resp.status_code, 400)


@moto.mock_s3
@test_context
def test_upload_batch_bad_algo(client):
    """A PUT to /batch with an algorithm that is not sha512 is rejected."""
    batch = mkbatch()
    batch['files']['one']['algorithm'] = 'md4'
    resp = upload_batch(client, batch)
    eq_(resp.status_code, 400)


@moto.mock_s3
@test_context
def test_upload_batch_bad_size(app, client):
    """A PUT to /batch with a file with the same hash and a different length
    is rejected"""
    batch = mkbatch()
    batch['files']['one']['size'] *= 2  # that ain't right!

    add_file_to_db(app, ONE)
    resp = upload_batch(client, batch)
    eq_(resp.status_code, 400)


@moto.mock_s3
@test_context
def test_upload_batch_success_fresh(client, app):
    """A PUT to /batch with a good batch succeeds, returns signed
    URLs expiring in one hour, and inserts the new batch into the DB
    with links to files, but no instances."""
    batch = mkbatch()
    with set_time():
        resp = upload_batch(client, batch)
        eq_(resp.status_code, 200)
        result = json.loads(resp.data)['result']
        eq_(result['author'], batch['author'])
        eq_(result['message'], batch['message'])
        eq_(result['files']['one']['algorithm'], 'sha512')
        eq_(result['files']['one']['size'], len(ONE))
        eq_(result['files']['one']['digest'], ONE_HASH)
        assert_signed_url(result['files']['one']['put_url'], ONE_HASH,
                          method='PUT', expires_in=3600)

    with app.app_context():
        tbl = tables.Batch
        batch_row = tbl.query.filter(tbl.id == result['id']).first()
    eq_(batch_row.author, batch['author'])
    eq_(batch_row.message, batch['message'])
    eq_(batch_row.files[0].size, len(ONE))
    eq_(batch_row.files[0].sha512, ONE_HASH)
    eq_(batch_row.files[0].instances, [])


@moto.mock_s3
@test_context
def test_upload_batch_success_some_existing_files(client, app):
    """A PUT to /batch with a good batch containing some files already present
    succeeds, returns signed URLs expiring in one hour, and inserts the new
    batch into the DB with links to files, but no instances."""
    batch = mkbatch()
    batch['files']['two'] = {
        'algorithm': 'sha512', 'size': len(TWO), 'digest': TWO_HASH}

    # make sure ONE is already in the DB with at least once instance
    inserted_id = add_file_to_db(app, ONE)

    with set_time():
        resp = upload_batch(client, batch)
        eq_(resp.status_code, 200)
        result = json.loads(resp.data)['result']
        eq_(result['files']['one']['algorithm'], 'sha512')
        eq_(result['files']['one']['size'], len(ONE))
        eq_(result['files']['one']['digest'], ONE_HASH)
        assert 'put_url' not in result['files']['one']
        eq_(result['files']['two']['algorithm'], 'sha512')
        eq_(result['files']['two']['size'], len(TWO))
        eq_(result['files']['two']['digest'], TWO_HASH)
        assert_signed_url(result['files']['two']['put_url'], TWO_HASH,
                          method='PUT', expires_in=3600)

    with app.app_context():
        tbl = tables.Batch
        batch_row = tbl.query.filter(tbl.id == result['id']).first()
    eq_(batch_row.author, batch['author'])
    eq_(batch_row.message, batch['message'])
    eq_(len(batch_row.files), 2)
    batch_row.files.sort(key=lambda f: f.size)
    eq_(batch_row.files[0].id, inserted_id)
    eq_(batch_row.files[1].size, len(TWO))
    eq_(batch_row.files[1].sha512, TWO_HASH)
    eq_(batch_row.files[1].instances, [])


@moto.mock_s3
@test_context
def test_legacy_get(client):
    """Getting /sha512/<digest> returns a 302 redirect to a signed URL"""
    with set_time():
        resp = client.get('/tooltool/sha512/{}'.format(ONE_HASH))
        assert_signed_302(resp, ONE_HASH)
