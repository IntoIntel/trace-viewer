# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest
import sys
import os
import json


from tvcm import dev_server
from tvcm import browser_controller
from tvcm import test_runner
from tvcm import resource_loader


_currently_active_module_test_suite = None


def _NavigateToTestCaseRunner(bc):
  bc.NavigateToPath('/tvcm/unittest/module_test_case_runner.html')
  bc.WaitForJavaScriptExpression('window.__readyToRun == true')
  # Sanity checks that __readyToRun is working right. If any of these pop,
  # it implies that __readyToRun isn't working.
  sanity_checks = [
    'window.tvcm !== undefined',
    'window.tvcm.GUID.allocate !== undefined',
    'window.tvcm.hasPanic !== undefined',
    'window.discoverTestsInModules !== undefined',
    'window.runTestNamed !== undefined'
  ]
  for check in sanity_checks:
    if not bc.EvaluateJavaScript(check):
      raise Exception('Load failed because sanity check %s failed')


class ModuleTestSuite(unittest.TestSuite):
  def __init__(self, project):
    super(ModuleTestSuite, self).__init__()
    self._project = project
    self._bc = None
    self._bc_startup_exception_string = None

  @property
  def __class__(self):
    def RecreateFunc():
      return self.recreateEmptyVersion()
    return RecreateFunc
  def recreateEmptyVersion(self):
    return ModuleTestSuite(self._project)

  def __call__(self, *args):
    return self.run(*args)

  def run(self, result):
    try:
      self.setUp()
      return super(ModuleTestSuite, self).run(result)
    finally:
      self.tearDown()

  @property
  def bc(self):
    return self._bc

  @property
  def bc_startup_exception_string(self):
    return self._bc_startup_exception_string

  def setUp(self):
    global _currently_active_module_test_suite
    if _currently_active_module_test_suite:
      self._bc_startup_exception_string = "Some previous suite did not shut down cleanly"
      self._bc = None
      return

    try:
      self._bc = browser_controller.BrowserController(self._project)
      _NavigateToTestCaseRunner(self._bc)
    except:
      import traceback
      traceback.print_exc()
      self._bc_startup_exception_string = traceback.format_exc()
      self._bc.Close()
      self._bc = None

    _currently_active_module_test_suite = self
    if self._bc:
      self._bc.stdout_enabled = True

  def tearDown(self):
    if self._bc:
      self._bc.stdout_enabled = False
      self._bc.Close()
      self._bc = None

    global _currently_active_module_test_suite
    _currently_active_module_test_suite = None

def DiscoverTestsInModule(project, start_path):
  try:
    return _DiscoverTestsInModuleImpl(project, start_path)
  except:
    import traceback
    sys.stderr.write("While discovering tests:\n")
    sys.stderr.write(sys.exc_info()[1].message)
    sys.stderr.write("\n\n")
    raise

def _DiscoverTestsInModuleImpl(project, start_path):
  if test_runner.PY_ONLY_TESTS:
    return unittest.TestSuite()

  if not browser_controller.IsSupported():
    raise Exception('Cannot run all tests: telemetry could not be found')
  rl = resource_loader.ResourceLoader(project)

  test_modules = [x.name for x in
                  project.FindAllTestModuleResources(start_path=start_path)]

  bc = browser_controller.BrowserController(project)
  try:
    _NavigateToTestCaseRunner(bc)
    if bc.EvaluateJavaScript('tvcm.hasPanic()'):
      raise Exception('Runner failure: %s' % bc.EvaluateJavaScript('tvcm.getPanicText()'))

    tests = bc.EvaluateThennableAndWait(
      'discoverTestsInModules(%s)' % json.dumps(test_modules))

    if bc.EvaluateJavaScript('tvcm.hasPanic()'):
      raise Exception('Test loading failure: %s' % bc.EvaluateJavaScript('tvcm.getPanicText()'))

    suite = ModuleTestSuite(project)
    for fully_qualified_test_name in tests:
      suite.addTest(ModuleTestCase(fully_qualified_test_name))
    return suite
  finally:
    bc.Close()



class ModuleTestCase(unittest.TestCase):
  def __init__(self, fully_qualified_test_name):
    super(ModuleTestCase, self).__init__(methodName='runTest')
    self.fully_qualified_test_name = fully_qualified_test_name

  def id(self):
    return self.fully_qualified_test_name

  def shortDescription(self):
    return None

  def __str__(self):
    i = self.fully_qualified_test_name.rfind('.')
    modname = self.fully_qualified_test_name[0:i]
    testname = self.fully_qualified_test_name[i+1:]
    return '%s (%s)' % (testname, modname)

  def runTest(self):
    global _currently_active_module_test_suite
    mts = _currently_active_module_test_suite
    assert mts, 'Something is wrong: ModuleTestCase can only be run inside a ModuleTestSuite.run()'

    if not mts.bc:
      raise Exception('Test cannot run because browser did not start.\n\nOriginal %s\n\n' % \
                      mts.bc_startup_exception_string)
    bc = mts.bc
    res = bc.EvaluateThennableAndWait(
      'runTestNamed(%s)' % json.dumps(self.fully_qualified_test_name))
