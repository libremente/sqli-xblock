"""TO-DO: Write a description of what this XBlock is."""
from django.template import Template, Context
import pkg_resources
import sqlite3
import json
from cgi import escape
from .lms_mixin import LmsCompatibilityMixin
from xblock.core import XBlock
from xblock.fields import Scope, Integer, List, String, Boolean, Float
from xblock.fragment import Fragment

class SqlInjectionXBlock(LmsCompatibilityMixin, XBlock):
    """
    TO-DO: document what your XBlock does.
    """

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    AVAILABLE_PROBLEMS = {
        'login': {
            'html': "static/html/login.html",
            'css': ["static/css/sqli.css"],
            'js': ["static/js/src/login.js"],
            'js_objs': ['SqlInjectionXBlock'],
            'log': 'previous_answers_login',
        },
        'union': {
            'html': "static/html/union.html",
            'css': ["static/css/sqli.css"],
            'js': [],
            'js_objs': [],
            'log': 'previous_answers_union',
        },
    }

    # TO-DO: delete count, and define your own fields.
    count = Integer(
        default=0, scope=Scope.user_state,
        help="A simple counter, to show something happening",
    )

    problem_id = String(
        default="login",
        scope=Scope.content,
        help="Chooses the specific problem in the suite of SQL injection problems"
    )

    done = Boolean(
        default=False,
        scope=Scope.user_state,
        help="Is student done with this problem"
    )

    student_attempts = Integer(
        default=0,
        scope=Scope.user_state,
        help="Number of attempts the student has made"
    )

    previous_answers_login = List(
        default=[], scope=Scope.user_state_summary,
        help="All previously entered answers, by all users, for the login problem"
    )

    previous_answers_union = List(
        default=[], scope=Scope.user_state_summary,
        help="All previously entered answers, by all users, for the union problem"
    )

    student_answer_username = String(
        default="",
        scope=Scope.user_state,
        help="student answer for username in login exercise"
    )

    student_answer_password = String(
        default="",
        scope=Scope.user_state,
        help="student answer for password in login exercise"
    )

    student_answer_category = String(
        default="",
        scope=Scope.user_state,
        help="student answer for category in union exercise"
    )

    student_score = Float(
        help="student's score on this problem",
        values={"min": 0, "step": .1},
        default=None,
        scope=Scope.user_state
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # TO-DO: change this view to display your data your own way.
    # Decorate the view in order to support multiple devices e.g. mobile
    # See: https://openedx.atlassian.net/wiki/display/MA/Course+Blocks+API
    # section 'View @supports(multi_device) decorator'
    @XBlock.supports("multi_device")
    def student_view(self, context=None):
        """
        The primary view of the SqlInjectionXBlock, shown to students
        when viewing courses.
        """
        if self.problem_id not in self.AVAILABLE_PROBLEMS:
            frag = Fragment(u"problem_id {} is not valid".format(self.problem_id))
            return frag

        problem_resources = self.AVAILABLE_PROBLEMS[self.problem_id]
        html = self.resource_string(problem_resources['html'])
        frag = Fragment(html.format(self=self))
        for css_file in problem_resources['css']:
            frag.add_css(self.resource_string(css_file))
        for js_file in problem_resources['js']:
            js_str = Template(self.resource_string(js_file)).render(
                Context({
                    'prev_answers_json': json.dumps(getattr(self, problem_resources['log'])),
                    'problem_score': self.student_score,
                    'problem_weight': self.weight,
                    'attempts': self.student_attempts,
                }))
            frag.add_javascript(js_str)
        for js_obj in problem_resources['js_objs']:
            frag.initialize_js(js_obj)
        return frag

    @XBlock.json_handler
    def login(self, data, suffix=''):
        db_conn = sqlite3.connect(pkg_resources.resource_filename(__name__, "static/dat/sqli.sqlite3"))
        db_conn.row_factory = sqlite3.Row
        cursor = db_conn.cursor()
        self.student_attempts += 1
        username = data['username']
        password = data['password']
        self.student_answer_username = username
        self.student_answer_password = password
        student_id = self.runtime.user_id if self.runtime.user_id is not None else self.scope_ids.user_id
        answer_string = "student_id: {} ||| username: {} ||| password: {}".format(
            student_id, username, password)
        self.previous_answers_login.append(answer_string)

        # NEVER, NEVER, NEVER do this yourself.  It's dangerous generate sql queries with string concatentation,
        # which is the point of this whole exercise
        sql_string = "SELECT * from users where username='{}' and password='{}'".format(username, password)
        try:
            result_user = cursor.execute(sql_string).fetchone()
            if result_user:
                if result_user['username'] == 'bob':
                    self.done = True
                    self.student_score = 1.0
                    self.runtime.publish(
                        self,
                        'grade',
                        {
                            'value': 1.0,
                            'max_value': 1.0,
                        }
                    )
                return {
                    'success': True,
                    'username': result_user['username'],
                    'email': result_user['email'],
                    'prev_answer': answer_string,
                    'attempts': self.student_attempts,
                    'student_score': "{:0.1f}".format(self.student_score) if self.student_score is not None else "None",
                }
        except (sqlite3.Error, sqlite3.Warning):
            pass

        return {
            'success': False,
            'username': None,
            'email': None,
            'prev_answer': answer_string,
            'attempts': self.student_attempts,
            'student_score': "{:0.1f}".format(self.student_score) if self.student_score is not None else "None",
        }

    def studio_view(self, context=None):
        html = self.resource_string("static/html/studio.html")
        frag = Fragment(html.format(self=self))
        frag.add_javascript(self.resource_string("static/js/src/studio_edit.js"))
        frag.initialize_js("SqlInjectionXBlockStudioEdit")
        return frag

    @XBlock.json_handler
    def change_problem(self, data, suffix=''):
        if 'problem_id' in data:
            self.problem_id = data['problem_id']


    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("SqlInjectionXBlock",
             """<vertical_demo>
                <sqli problem_id="login"/>
                <sqli problem_id="union"/>
                </vertical_demo>
             """),
        ]
