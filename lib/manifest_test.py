
from nose.tools import *
import manifest from './manifest'


def test_iter_fields():
  payload = {
    "name": "test",
    "dependencies": {
      "a": "b"
    },
    "cfg(dev).foobar": "Simsalabim",
    "cfg(dev).dependencies": {
      "c": "d"
    },
    "cfg(prod)": {
      "name": "test-in-dev-mode",
      "dependencies": {
        "e": "f"
      }
    }
  }
  result = sorted(manifest.iter_fields(payload), key=lambda x: (x[0] or '', x[1] or ''))
  assert_equals(result, [(None, 'dependencies', {'a': 'b'}), (None, 'name', 'test'), ('cfg(dev)', 'dependencies', {'c': 'd'}), ('cfg(dev)', 'foobar', 'Simsalabim'), ('cfg(prod)', 'dependencies', {'e': 'f'}), ('cfg(prod)', 'name', 'test-in-dev-mode')])
  result = sorted(manifest.iter_fields(payload, 'dependencies'), key=lambda x: x[0] or '')
  assert_equals(result, [(None, {'a': 'b'}), ('cfg(dev)', {'c': 'd'}), ('cfg(prod)', {'e': 'f'})])
