# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# XXX Much of this functionality should probably be its own
#     Separate relengapi blueprint

from flask import current_app
from bzrest.client import BugzillaClient

from relengapi.blueprints.slaveloan.model import History
from relengapi.blueprints.slaveloan.model import Loans

MAX_ALIAS = 15


def _bzclient():
    if current_app.get('bzclient', None):
        return current_app.bzclient
    bzclient = BugzillaClient()
    bzclient.configure(bzurl=current_app.config['BUGZILLA_URL'],
                       username=current_app.config['BUGZILLA_USER'],
                       password=current_app.config['BUGZILLA_PASS'])
    current_app.bzclient = bzclient
    return current_app.bzclient


class Bug(object):
    alias = None
    id = None
    
    def __init__(self, id_=None, loadInfo=True):
        if isinstance(id_, int):
            self.id = id_
        else:
            self.alias = id_
        self.data = {}
        if id_ and loadInfo:
            self.refresh()
    
    def refresh(self):
        self.data = _bzclient().get_bug(self.id)
        self.id = self.data["id"]
        self.alias = self.data["alias"]


class ProblemTrackingBug(Bug):
    product = "Release Engineering"
    component = "Buildduty"
    
    def __init__(self, slave_name, *args, **kwargs):
        self.slave_name = slave_name
        Bug.__init__(self, id_=slave_name, *args, **kwargs)
    
    def create(self, comment=None):
        if len(self.slave_name) > MAX_ALIAS:
            alias = None
        else:
            alias = self.slave_name
        data = {
            "product": self.product,
            "component": self.component,
            "summary": "%s problem tracking" % self.slave_name,
            "version": "other",
            "alias": alias,
            # todo: do we care about setting these correctly?
            "op_sys": "All",
            "platform": "All"
        }
        if comment:
            data['comment'] = comment
        resp = _bzclient().create_bug(data)
        self.id = resp["id"]


class LoanerBug(Bug):
    product = "Release Engineering"
    component = "Loan Requests"
    
    def __init__(self, *args, **kwargs):
        Bug.__init__(self, *args, **kwargs)
    
    def create(cls, summary=None, comment=None, blocks=None):
        data = {
            "product": self.product,
            "component": self.component,
            "summary": summary,
            "version": "other",
            # todo: do we care about setting these correctly?
            "op_sys": "All",
            "platform": "All"
        }
        if comment:
            data['comment'] = comment
        if blocks:
            data['blocks'] = blocks
        resp = _bzclient().create_bug(data)
        self.id = resp["id"]
        return self


LOAN_SUMMARY = u"Loan a slave of {slave_class} to {human}"
COMMENT_ZERO = u"""{human} is in need of a slaveloan from slave class {slave_class}

(this bug was auto-created from the slaveloan tool)
{loan_url}"""


def create_loan_bug(loan_id=None, slave_class=None):
    session = current_app.db.session('relengapi')
    l = session.query(Loans).get(loanid)
    summary = LOAN_SUMMARY.format(slave_class=slave_class,
                                  human=l.human.bugzilla)
    c_zero = COMMENT_ZERO.format(
        slave_class=slave_class,
        human=l.human.bugzilla,
        loan_url=url_for("slaveloan.loan_details", id=loan_id))
    loan_bug = LoanerBug(loadInfo=False)
    bug_id = loan_bug.create(comment=c_zero, summary=summary)
    return bug_id

"""    l.bug_id = bug_id
    history = History(for_loan=l,
                      timestamp=tz.utcnow(),
                      msg="Created bug {id} for loan".format(id=bug_id))
    session.add(l)
    session.add(h)
    session.commit()"""