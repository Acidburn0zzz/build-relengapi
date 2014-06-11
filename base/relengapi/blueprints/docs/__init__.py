# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import shutil
from relengapi import subcommands
import pkg_resources
from flask import Blueprint
from flask import jsonify
from flask import abort
from flask import current_app
from flask import render_template
from flask import send_from_directory
from sphinx.websupport import WebSupport
from sphinx.websupport.errors import DocumentNotFoundError
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('docs', __name__,
               template_folder='templates')
bp.root_widget_template('docs_root_widget.html', priority=100)


def get_builddir():
    if 'DOCS_BUILD_DIR' in current_app.config:
        return current_app.config['DOCS_BUILD_DIR']
    relengapi_dist = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse('relengapi'))
    return os.path.join(
        pkg_resources.resource_filename(relengapi_dist.as_requirement(), ''),
        'docs_build_dir')


def get_support(force=False):
    if not hasattr(current_app, 'docs_websupport') or force:
        builddir = get_builddir()
        # this is where files installed by setup.py's data_files go..
        srcdir = os.path.join(sys.prefix, 'relengapi-docs')
        current_app.docs_websupport = WebSupport(
            srcdir=srcdir,
            builddir=builddir,
            staticroot='/docs/static',
            docroot='/docs')
    return current_app.docs_websupport


@bp.record
def check_built(state):
    with state.app.app_context():
        support = get_support()
        if not os.path.exists(os.path.join(support.builddir, 'data', '.buildinfo')):
            logger.warning("docs have not been built")


@bp.route('/', defaults={'docname': 'index'})
@bp.route('/<path:docname>')
def doc(docname):
    try:
        doc = get_support().get_document(docname.strip('/'))
    except DocumentNotFoundError:
        abort(404)
    return render_template('doc.html', document=doc)


@bp.route('/static', defaults={'path': ''})
@bp.route('/static/<path:path>')
def static(path):
    # the Blueprint's static_folder can't depend on app configuration, so we
    # just implement static files directly
    support = get_support()
    return send_from_directory(support.staticdir, path)


def api_info(docname):
    rv = []
    vfs = current_app.view_functions
    for map_elt in current_app.url_map.iter_rules():
        func = vfs[map_elt.endpoint]
        if func.__doc__ and func.__doc__.startswith('API:'):
            rv.append((map_elt.rule, func.__doc__))
    return jsonify(rv)


class BuildDocsSubcommand(subcommands.Subcommand):

    def make_parser(self, subparsers):
        parser = subparsers.add_parser('build-docs',
                                       help='make a built version of the '
                                            'sphinx documentation')
        parser.add_argument("--debug", action='store_true',
                            help="Show debug logging")
        return parser

    def run(self, parser, args):
        if not args.debug:
            logger.setLevel(logging.INFO)

        # always start with a fresh build dir
        builddir = get_builddir()
        if os.path.exists(builddir):
            shutil.rmtree(builddir)
        os.makedirs(builddir)

        # now that the source is accumulated, build it; force get_support
        # to create a fresh WebSupport object since it creates some directories
        # in its constructor, which may have been called before the builddir
        # was erased.
        get_support(force=True).build()
