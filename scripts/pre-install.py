
from __future__ import print_function
import os
import subprocess

package_root = module.directory.parent
gitref = package_root.joinpath('.gitref')
gitdir = package_root.joinpath('.git')
has_gitref = gitref.is_file()
has_gitdir = gitdir.is_dir()
if not has_gitref and not has_gitdir:
  print('[nodepy-pm/scripts/pre-install]: can not create .gitref if .git directory does not exist.')
elif has_gitdir:
  try:
    refname = subprocess.check_output(['git', 'describe', '--all', '--long'], cwd=str(package_root)).decode()
  except (subprocess.CalledProcessError, OSError) as e:
    print('[nodepy-pm/scripts/pre-install]: could not create .gitref ({})'.format(e))
  else:
    with gitref.open('w') as fp:
      fp.write(refname.strip())
      fp.write(u'\n')
