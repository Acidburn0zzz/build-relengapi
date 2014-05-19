# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from relengapi import subcommands
from relengapi import celery
from flask import Blueprint
from flask import current_app
import logging
import sys

bp = Blueprint('base', __name__)
logger = logging.getLogger(__name__)


class ServeSubcommand(subcommands.Subcommand):

    def make_parser(self, subparsers):
        parser = subparsers.add_parser('serve', help='run the server')
        parser.add_argument("-a", "--all-interfaces", action='store_true',
                            help='Run on all interfaces, not just localhost')
        parser.add_argument("-p", "--port", type=int, default=5000,
                            help='Port on which to serve')
        parser.add_argument("--no-debug", action='store_true',
                            help="Don't run in debug mode")
        return parser

    def run(self, parser, args):
        kwargs = {}
        if args.all_interfaces:
            kwargs['host'] = '0.0.0.0'
        kwargs['debug'] = not args.no_debug
        kwargs['port'] = args.port
        current_app.run(**kwargs)


class CreateDBSubcommand(subcommands.Subcommand):

    def make_parser(self, subparsers):
        parser = subparsers.add_parser(
            'createdb', help='create configured databases')
        return parser

    def run(self, parser, args):
        for dbname in current_app.db.database_names:
            logger.info(" * creating tables for database %s", dbname)
            meta = current_app.db.metadata[dbname]
            engine = current_app.db.engine(dbname)
            meta.create_all(bind=engine)


class RunTestsSubcommand(subcommands.Subcommand):

    want_logging = False

    def make_parser(self, subparsers):
        parser = subparsers.add_parser(
            'run-tests', help='run RelengAPI tests')
        parser.add_argument("nose_args", metavar='NOSE-ARGS', nargs='*',
                            help="Arguments to nosetests")
        return parser

    def run(self, parser, args):
        import nose
        sys.argv = [sys.argv[0]] + args.nose_args
        nose.main()

# testing stuff

# these are temporary routes used to test functionality that's not yet used for
# "real" work


@celery.task
def add(x, y, z):
    return x + y + z


@bp.route('/temp/test-celery')
def test_celery():
    """Test out a celery task"""
    answer = add.delay(1, 2, 3).get()
    return "1 + 2 + 3, according to the remote celery node, is %d" % answer
