# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import re
import time
import calendar
import sqlalchemy as sa
import dateutil.parser
from sqlalchemy import orm
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from relengapi import db
from flask import Blueprint
from flask import g
from flask import abort
from flask import request
from flask import jsonify
from flask import Response

from relengapi import actions

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)
bp = Blueprint('mapper', __name__)

actions.mapper.mapping.insert.doc("Allows new hg-git mappings to be inserted "
                                  "into mapper db (hashes table)")
actions.mapper.project.insert.doc("Allows new projects to be inserted into "
                                  "mapper db (projects table)")

# TODO: replace abort with a custom exception - http://flask.pocoo.org/docs/patterns/apierrors/

class Project(db.declarative_base('mapper')):
    __tablename__ = 'projects'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), nullable=False, unique=True)


class Hash(db.declarative_base('mapper')):
    __tablename__ = 'hashes'
    hg_changeset = sa.Column(sa.String(40), nullable=False)
    git_commit = sa.Column(sa.String(40), nullable=False)
    project_id = sa.Column(sa.Integer, sa.ForeignKey('projects.id'), nullable=False)
    project = orm.relationship(Project, primaryjoin=(project_id == Project.id))
    # project = orm.relationship(Project, backref=orm.backref('hashes', order_by=id))
    date_added = sa.Column(sa.Integer, nullable=False)

    project_name = property(lambda self: self.project.name)

    def as_json(self):
        return jsonify(**{n: getattr(self, n)
                          for n in ('git_commit', 'hg_changeset', 'date_added', 'project_name')})

    __table_args__ = (
        # TODO: (needs verification) all queries specifying a hash are for
        # (project, hash), so these aren't used
        sa.Index('hg_changeset', 'hg_changeset'),
        sa.Index('git_commit', 'git_commit'),
        # TODO: this index is a prefix of others and will never be used
        sa.Index('project_id', 'project_id'),
        sa.Index('project_id__date_added', 'project_id', 'date_added'),
        sa.Index('project_id__hg_changeset', 'project_id', 'hg_changeset', unique=True),
        sa.Index('project_id__git_commit', 'project_id', 'git_commit', unique=True),
    )

    __mapper_args__ = {
        # tell the SQLAlchemy ORM about one of the unique indexes; it doesn't matter which
        'primary_key': [project_id, hg_changeset],
    }


def _project_filter(projects_arg):
    """ Helper method that returns the sqlalchemy filter expression for the
    project name(s) specified. This can be a comma-separated list, which is
    the way we combine queries across multiple projects.

    Args:
        projects_arg: a comma-separated list of project names

    Returns:
        A SQLAlchemy filter expression
    """
    if ',' in projects_arg:
        return Project.name.in_(projects_arg.split(','))
    else:
        return Project.name == projects_arg


def _build_mapfile(query):
    """ Helper method to build a map file from a sqlalchemy query.
    Args:
        query: the sqlalchemy query

    Returns:
        * Text output: 40 characters git commit sha, a space,
          40 characters hg changeset sha, a newline; or
        * None if the query returns no results
    """
    contents = '\n'.join('%s %s' % (r.git_commit, r.hg_changeset) for r in query)
    if contents:
        return Response(contents + '\n', mimetype='text/plain')


def _check_well_formed_sha(vcs, sha, exact_length=40):
    """Helper method to check for a well-formed sha.
    Args:
        vcs: the name of the vcs system ('hg' or 'git')
        sha: string to check against the well-formed sha regex

    Returns:
        None

    Exceptions:
        HTTP 400: on malformed sha, via flask.abort()
    """
    if vcs not in ("git", "hg"):
        abort(400, "Unknown vcs type %s" % vcs)
    rev_regex = re.compile('''^[a-f0-9]{1,40}$''')
    if sha is None:
        abort(400, "%s SHA is <None>" % vcs)
    elif sha == "":
        abort(400, "%s SHA is an empty string" % vcs)
    elif not rev_regex.match(sha):
        abort(400, "%s SHA contains bad characters: '%s'" % (vcs, str(sha)))
    if exact_length is not None and len(sha) != exact_length:
        abort(400, "%s SHA should be %s characters long, but is %s characters long: '%s'"
              % (vcs, exact_length, len(sha), str(sha)))


def _get_project(session, project):
    try:
        return Project.query.filter_by(name=project).one()
    except MultipleResultsFound:
        abort(404, "Multiple projects with name %s found in database" % project)
    except NoResultFound:
        abort(404, "Could not find project %s in database" % project)


def _add_hash(session, git_commit, hg_changeset, project):
    _check_well_formed_sha('git', git_commit)
    _check_well_formed_sha('hg', hg_changeset)
    h = Hash(git_commit=git_commit, hg_changeset=hg_changeset, project=project,
             date_added=time.time())
    session.add(h)


@bp.route('/<projects>/rev/<vcs_type>/<commit>')
def get_rev(projects, vcs_type, commit):
    """Return the hg changeset sha for a git commit id, or vice versa.

    Args:
        projects: comma-delimited project names(s) string
        vcs: the string 'hg' or 'git' to categorize the commit you are passing
              (not the type you wish to receive back)
        commit: revision or partial revision string of sha to be converted

    Returns:
        (git_commit hg_changeset\n)

    Exceptions:
        HTTP 400: if an unknown vcs
        HTTP 400: if a badly formed sha
        HTTP 404: if row not found
    """
    _check_well_formed_sha(vcs_type, commit, exact_length=None)
    q = Hash.query.join(Project).filter(_project_filter(projects))
    if vcs_type == "git":
        q = q.filter("git_commit like :cspatttern").params(cspatttern=commit+"%")
    elif vcs_type == "hg":
        q = q.filter("hg_changeset like :cspatttern").params(cspatttern=commit+"%")
    try:
        row = q.one()
        return "%s %s" % (row.git_commit, row.hg_changeset)
    except NoResultFound:
        return "not found", 404
    except MultipleResultsFound:
        return "internal error - multiple results returned, should not be possible in database", 500


@bp.route('/<projects>/mapfile/full')
def get_full_mapfile(projects):
    """Get a map file containing mappings for one or more projects.

    Args:
        projects: comma-delimited project names(s) string

    Returns:
        A map file containing all SHA mappings for the specified project(s) as
        lines (git_commit hg_changeset\n), ordered by hg sha, with mime type
        'text/plain'

    Exceptions:
        HTTP 404: No results found
    """
    q = Hash.query.join(Project).filter(_project_filter(projects))
    q = q.order_by(Hash.hg_changeset)
    mapfile = _build_mapfile(q)
    if not mapfile:
        abort(404, 'No results found in database for requested map file')
    return mapfile


@bp.route('/<projects>/mapfile/since/<since>')
def get_mapfile_since(projects, since):
    """Get a map file since date.

    Args:
        projects: comma-delimited project names(s) string
        since: a timestamp, in a format parsed by [dateutil.parser.parse]
            (https://labix.org/python-dateutil)
            evaluated based on the time the record was inserted into mapper
            database, not the time of commit and not the time of conversion.

    Returns:
        A map file containing all SHA mappings for the specified project(s) as
        lines (git_commit hg_changeset\n), ordered by hg sha, with mime type
        'text/plain', inserted in the mapper database since the time given

    Exceptions:
        HTTP 404: No results found
    """
    try:
        since_dt = dateutil.parser.parse(since)
    except ValueError as e:
        abort(400, 'Invalid date %s specified; see https://labix.org/python-dateutil: %s' % (since, e.message))
    since_epoch = calendar.timegm(since_dt.utctimetuple())
    q = Hash.query.join(Project).filter(_project_filter(projects))
    q = q.order_by(Hash.hg_changeset)
    q = q.filter(Hash.date_added > since_epoch)
    print q
    mapfile = _build_mapfile(q)
    if not mapfile:
        abort(404, 'No mappings inserted into database for project(s) %s since %s' % (projects, since))
    return mapfile


def _insert_many(project, ignore_dups=False):
    """Update the database with many git-hg mappings.

    Args:
        project: single project name string
        ignore_dups: boolean.  If False, abort on duplicate entries without inserting
        anything

    Returns:
        An empty json response body

    Exceptions:
        HTTP 400: if the content-type is incorrect
        HTTP 409: if ignore_dups=False and there were duplicate entries
    """
    if request.content_type != 'text/plain':
        abort(400, "HTTP request header 'Content-Type' must be set to 'text/plain'")
    session = g.db.session('mapper')
    proj = _get_project(session, project)
    for line in request.stream.readlines():
        line = line.rstrip()
        try:
            (git_commit, hg_changeset) = line.split(' ')
        except ValueError:
            logger.error("Received input line: '%s' for project %s", line, project)
            logger.error("Was expecting an input line such as "
                         "'686a558fad7954d8481cfd6714cdd56b491d2988 "
                         "fef90029cb654ad9848337e262078e403baf0c7a'")
            logger.error("i.e. where the first hash is a git commit SHA "
                         "and the second hash is a mercurial changeset SHA")
            abort(400, "Input line '%s' received for project %s did not contain a space" % (line, project))
            # header/footer won't match this format
            continue
        _add_hash(session, git_commit, hg_changeset, proj)
        if ignore_dups:
            try:
                session.commit()
            except sa.exc.IntegrityError:
                session.rollback()
    if not ignore_dups:
        try:
            session.commit()
        except sa.exc.IntegrityError:
            abort(409, "Some of the given mappings for project %s already exist" % project)
    return jsonify()


@bp.route('/<project>/insert', methods=('POST',))
@actions.mapper.mapping.insert.require()
def insert_many_no_dups(project):
    """Insert many git-hg mapping entries via POST, and error on duplicate SHAs.

    Args:
        project: single project name string
        POST data: map file lines (git_commit hg_changeset\n)
        Content-Type: text/plain

    Returns:
        An empty json response body

    Exceptions:
        HTTP 409: if there were duplicate entries
        HTTP 400: if the request content-type is not 'text/plain'
    """
    return _insert_many(project, ignore_dups=False)


@bp.route('/<project>/insert/ignoredups', methods=('POST',))
@actions.mapper.mapping.insert.require()
def insert_many_ignore_dups(project):
    """Insert many git-hg mapping entries via POST, allowing duplicate SHAs.

    Args:
        project: single project name string
        POST data: map file lines (git_commit hg_changeset\n)
        Content-Type: text/plain

    Returns:
        An empty json response body

    Exceptions:
        HTTP 400: if the request content-type is not 'text/plain'
    """
    return _insert_many(project, ignore_dups=True)


@bp.route('/<project>/insert/<git_commit>/<hg_changeset>', methods=('POST',))
@actions.mapper.mapping.insert.require()
def insert_one(project, git_commit, hg_changeset):
    """Insert a single git-hg mapping.

    Args:
        project: single project name string
        git_commit: 40 char hexadecimal string
        hg_changeset: 40 char hexadecimal string

    Returns:
        a json representation of the inserted data:
        {
            'date_added': <date>,
            'project_name': <project>,
            'git_commit': <git sha>,
            'hg_changeset': <hg sha>,
        }

    Exceptions:
        HTTP 500: No results found
        HTTP 409: Mapping already exists for this project
        HTTP 400: Badly formed sha
    """
    session = g.db.session('mapper')
    proj = _get_project(session, project)
    _add_hash(session, git_commit, hg_changeset, proj)
    try:
        session.commit()
        q = Hash.query.join(Project).filter(_project_filter(project))
        inserted_hash = q.filter("git_commit == :commit").params(commit=git_commit).one()
        return inserted_hash.as_json()
    except sa.exc.IntegrityError:
        abort(409, "Provided mapping %s %s for project %s already exists and cannot be reinserted" % (git_commit, hg_changeset, project))
    except NoResultFound:
        abort(500, "Provided mapping %s %s for project %s could not be inserted into the database" % (git_commit, hg_changeset, project))
    except MultipleResultsFound:
        abort(500, "Provided mapping %s %s for project %s has been inserted into the database multiple times" % (git_commit, hg_changeset, project))


@bp.route('/<project>', methods=('POST',))
@actions.mapper.project.insert.require()
def add_project(project):
    """Insert a new project into the database.

    Args:
        project: single project name string

    Returns:
        An empty json response body

    Exceptions:
        HTTP 409 if the project already exists
    """

    session = g.db.session('mapper')
    p = Project(name=project)
    session.add(p)
    try:
        session.commit()
    except (sa.exc.IntegrityError, sa.exc.ProgrammingError):
        abort(409, "Project %s could not be inserted into the database" % project)
    return jsonify()
