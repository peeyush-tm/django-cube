__doc__ = """
In your settings, use

  TEST_RUNNER = 'ambidjangolib.test.simple.run_tests_until_fail'

to make `manage.py test` stop after the first test suite with failures, and
only show the first failing test in the suite.
"""


from unittest import \
     TestSuite, TextTestRunner, _TextTestResult, defaultTestLoader
from django.test import _doctest as doctest
from django.conf import settings
from django.db import transaction, connection
from django.db.models import get_app, get_apps
from django.test.utils import \
     setup_test_environment, teardown_test_environment
from django.test.simple import build_test, get_tests, doctestOutputChecker
from django.test.testcases import DocTestRunner

try:
    # pre-Django-1.0
    from django.test.utils import create_test_db, destroy_test_db
except ImportError:
    # post-Django-1.0
    def create_test_db(*args, **kwargs):
        connection.creation.create_test_db(*args, **kwargs)
    def destroy_test_db(*args, **kwargs):
        connection.creation.destroy_test_db(*args, **kwargs)

class DocTestRunner(doctest.DocTestRunner):
    """
    Replacement for django.test.testcases.DocTestRunner which unfortunately
    overrides any supplied `optionflags=` kwarg with only `doctest.ELLIPSIS`.
    We need to pass on optionflags.
    """
    def __init__(self, *args, **kwargs):
        doctest.DocTestRunner.__init__(self, *args, **kwargs)
        self.optionflags |= doctest.ELLIPSIS
        # Django's original has `=` instead of `|=` here

    def report_unexpected_exception(self, out, test, example, exc_info):
        doctest.DocTestRunner.report_unexpected_exception(self, out, test,
                                                          example, exc_info)
        # Rollback, in case of database errors. Otherwise they'd have
        # side effects on other tests.
        transaction.rollback_unless_managed()


def _add_tests_for_module(suite, module):
    """
    Repeated code from inside `build_suite()` is refactored here.
    """
    # Load unit and doctests in the given module. If module has a suite()
    # method, use it. Otherwise build the test suite ourselves.
    if hasattr(module, 'suite'):
        suite.addTest(module.suite())
    else:
        suite.addTest(defaultTestLoader.loadTestsFromModule(module))
        try:
            suite.addTest(doctest.DocTestSuite(
                module,
                checker=doctestOutputChecker,
                runner=DocTestRunner,
                optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
        except ValueError:
            # No doc tests in models.py
            pass


def build_suite(app_module):
    """
    Create a complete Django test suite for the provided application module.

    This overrides Django's original `django.test.simple.build_suite()` because
    we need to pass the `REPORT_ONLY_FIRST_FAILURE` option flag to
    `DocTestSuite` instances.
    """
    suite = TestSuite()

    _add_tests_for_module(suite, app_module)

    # Check to see if a separate 'tests' module exists parallel to the
    # models module
    test_module = get_tests(app_module)
    if test_module:
        _add_tests_for_module(suite, test_module)

    return suite


class _FailStopTextTestResult(_TextTestResult):
    def addError(self, test, err):
        _TextTestResult.addError(self, test, err)
        self.shouldStop = True

    def addFailure(self, test, err):
        _TextTestResult.addFailure(self, test, err)
        self.shouldStop = True


class FailStopTextTestRunner(TextTestRunner):
    def _makeResult(self):
        return _FailStopTextTestResult(
            self.stream, self.descriptions, self.verbosity)


def run_tests_until_fail(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    """
    Run the unit tests for all the test labels in the provided list.
    Labels must be of the form:
     - app.TestClass.test_method
        Run a single specific test method
     - app.TestClass
        Run all the test methods in a given class
     - app
        Search for doctests and unittests in the named application.

    When looking for tests, the test runner will look in the models and
    tests modules for the application.

    A list of 'extra' tests may also be provided; these tests
    will be added to the test suite.

    Stops the tests at the first failure and returns 1.  If all test pass,
    returns 0.

    Also displays only the first failure in the failing test suite.
    """
    setup_test_environment()

    settings.DEBUG = False
    suite = TestSuite()

    if test_labels:
        for label in test_labels:
            if '.' in label:
                suite.addTest(build_test(label))
            else:
                app = get_app(label)
                suite.addTest(build_suite(app))
    else:
        for app in get_apps():
            suite.addTest(build_suite(app))

    for test in extra_tests:
        suite.addTest(test)

    old_name = settings.DATABASE_NAME
    create_test_db(verbosity, autoclobber=not interactive)
    result = FailStopTextTestRunner(verbosity=verbosity).run(suite)
    destroy_test_db(old_name, verbosity)

    teardown_test_environment()

    return len(result.failures) + len(result.errors)
