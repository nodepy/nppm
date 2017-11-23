# Copyright (c) 2017 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
Helper function to create script files for pure Python code, ppy modules or
shell commands. Uses the Python #distlib package.
"""

import os
import six
try:
  from distlib.scripts import ScriptMaker as _ScriptMaker
except ImportError as exc:
  from pip._vendor.distlib.scripts import ScriptMaker as _ScriptMaker

import argschema from '../argschema'


class ScriptMaker:
  """
  Our own script maker class. It is unlike #distutils.script.ScriptMaker.
  """

  def __init__(self, directory, location):
    assert location in ('root', 'global', 'local')
    self.directory = directory
    self.location = location
    self.path = []
    self.pythonpath = []

  def _init_code(self):
    code = (
      '# Initialize environment variables (from ScriptMaker).\n'\
      'import os, sys\n'
    )
    if self.path:
      path = [os.path.abspath(x) for x in self.path]
      code += (
        'os.environ["PATH"] = os.pathsep.join({path!r}) + os.pathsep + os.environ.get("PATH", "")\n'
        .format(path=path)
      )
    code += 'sys.path.extend({pythonpath!r})\n'.format(
      pythonpath=[os.path.abspath(x) for x in self.pythonpath]
    )
    # Remember: We don't set PYTHONPATH due to nodepy/nodepy#62
    return code

  def _get_maker(self):
    return _ScriptMaker(None, self.directory)

  def get_files_for_script_name(self, script_name):
    """
    Returns the filenames that would be created by one of the `make_...()`
    functions.
    """

    maker = self._get_maker()

    # Reproduces _ScriptMaker._write_script() a little bit.
    use_launcher = maker.add_launchers and maker._is_nt
    outname = os.path.join(maker.target_dir, script_name)
    if use_launcher:
      n, e = os.path.splitexst(script_name)
      if e.startswith('.py'):
        outname = n
      outname = '{}.exe'.format(outname)
    else:
      if maker._is_nt and not outname.endswith('.py'):
        outname += '.py'
    return [outname]

  def make_python(self, script_name, code):
    """
    Uses #distlib.scripts.ScriptMaker to create a Python script that is invoked
    with this current interpreter. The script runs *code* and will be created
    in the *directory* specified in the constructor of this #ScriptMaker.

    # Parameters
    script_name (str): The name of the script to create.
    code (str): The python code to run.

    # Returns
    A list of filenames created. Depending on the platform, more than one file
    might be created to support multiple use cases (eg. and `.exe` but also a
    bash-script on Windows).
    """

    if os.name == 'nt' and (not script_name.endswith('.py') \
        or not script_name.endswith('.pyw')):
      # ScriptMaker._write_script() will split the extension from the script
      # name, thus if there is an extension, we should add another suffix so
      # the extension doesn't get lost.
      script_name += '.py'

    maker = self._get_maker()
    maker.clobber = True
    maker.variants = set(('',))
    maker.set_mode = True
    maker.script_template = self._init_code() + code
    return maker.make(script_name + '=isthisreallynecessary')

  def make_command(self, script_name, args):
    """
    Uses #make_python() to create a Python script that uses the #subprocess
    module to run the command specified with *args*.
    """

    code = 'import sys, subprocess, os\n'\
           'os.environ["PYTHONPATH"] = os.pathsep.join({pythonpath!r}) + os.pathsep + os.environ.get("PYTHONPATH", "")\n'\
           'sys.exit(subprocess.call({!r} + sys.argv[1:]))\n'.format(args, pythonpath=self.pythonpath)
    return self.make_python(script_name, code)

  def make_nodepy(self, script_name, filename):
    """
    Uses #make_pyton() to create a script that invokes the current Python and
    Node.py runtime to run the Node.py module specified by *filename*.
    """

    args = ['--keep-arg0']
    args.append(filename)

    code = (
      'import sys, nodepy.main, nodepy.runtime\n'
      'nodepy.runtime.script = {{"location": {location!r}, "original_path": sys.path[:]}}\n'
      'sys.argv = [sys.argv[0]] + {args!r} + sys.argv[1:]\n'
      'sys.exit(nodepy.main.main())\n'
      .format(args=args, location=self.location)
    )
    return self.make_python(script_name, code)

  def make_wrapper(self, script_name, target_program):
    """
    Creates a Python wrapper script that will invoke *target_program*. Before
    the program is invoked, the environment variables PATH and PYTHONPATH will
    be prefixed with the paths from *path* and *pythonpath*.
    """

    if isinstance(target_program, str):
      if not os.path.isabs(target_program):
        raise ValueError('target_program must be an absolute path')
      target_program = [target_program]

    return self.make_command(script_name, target_program)
