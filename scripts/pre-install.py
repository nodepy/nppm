# The MIT License (MIT)
#
# Copyright (c) 2017-2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import print_function
import os
import subprocess

package_root = module.directory.parent
gitref = package_root.joinpath('.gitref')
gitdir = package_root.joinpath('.git')
has_gitref = gitref.is_file()
has_gitdir = gitdir.is_dir()
if not has_gitref and not has_gitdir:
  print('[nppm/scripts/pre-install]: can not create .gitref if .git directory does not exist.')
elif has_gitdir:
  try:
    refname = subprocess.check_output(['git', 'describe', '--all', '--long'], cwd=str(package_root)).decode()
  except (subprocess.CalledProcessError, OSError) as e:
    print('[nppm/scripts/pre-install]: could not create .gitref ({})'.format(e))
  else:
    with gitref.open('w') as fp:
      fp.write(refname.strip())
      fp.write(u'\n')
