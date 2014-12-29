# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import mock

from moto import mock_sqs
from nose.tools import assert_raises
from nose.tools import eq_
from relengapi.lib.testing.context import TestContext

test_context = TestContext(reuse_app=False)

aws_cfg = {
    'AWS': {
        'access_key_id': 'aa',
        'secret_access_key': 'ss',
    },
}


@mock_sqs
@test_context.specialize(config=aws_cfg)
def test_connect_to(app):
    with mock.patch('boto.connect_sqs', return_value='sqs_conn') as connect_sqs:
        eq_(app.aws.connect_to('sqs', 'us-east-1'), 'sqs_conn')
        connect_sqs.assert_called_with(
            aws_access_key_id='aa',
            aws_secret_access_key='ss',
            region=mock.ANY)
    # connection is cached
    eq_(app.aws.connect_to('sqs', 'us-east-1'), 'sqs_conn')


@mock_sqs
@test_context
def test_connect_to_no_creds(app):
    with mock.patch('boto.connect_sqs', return_value='sqs_conn') as connect_sqs:
        eq_(app.aws.connect_to('sqs', 'us-east-1'), 'sqs_conn')
        connect_sqs.assert_called_with(
            # the None here will cause boto to look in ~/.boto, etc.
            aws_access_key_id=None,
            aws_secret_access_key=None,
            region=mock.ANY)


@mock_sqs
@test_context
def test_connect_to_invalid_region(app):
    assert_raises(RuntimeError, lambda:
                  app.aws.connect_to('sqs', 'us-canada-17'))


@mock_sqs
@test_context.specialize(config=aws_cfg)
def test_get_sqs_queue_no_queue(app):
    assert_raises(RuntimeError, lambda:
                  app.aws.get_sqs_queue('us-east-1', 'missing'))


@mock_sqs
@test_context.specialize(config=aws_cfg)
def test_get_sqs_queue(app):
    conn = app.aws.connect_to('sqs', 'us-east-1')
    conn.create_queue('my-sqs-queue')
    queue = app.aws.get_sqs_queue('us-east-1', 'my-sqs-queue')
    # check it's a queue
    assert hasattr(queue, 'get_messages')
    # check caching
    assert app.aws.get_sqs_queue('us-east-1', 'my-sqs-queue') is queue


@mock_sqs
@test_context.specialize(config=aws_cfg)
def test_sqs_write(app):
    conn = app.aws.connect_to('sqs', 'us-east-1')
    queue = conn.create_queue('my-sqs-queue')
    app.aws.sqs_write('us-east-1', 'my-sqs-queue', {'a': 'b'})
    msgs = queue.get_messages()
    assert len(msgs) == 1
    eq_(json.loads(msgs[0].get_body()), {'a': 'b'})
