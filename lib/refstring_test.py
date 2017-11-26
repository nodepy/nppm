
from nose.tools import *
import {Package, Ref, parse, parse_package} from './refstring'
import {Version, Selector} from './semver'


def test_parse():
  assert_equals(parse('foobar'), Ref(Package(None, 'foobar'), None, None, None))
  assert_equals(parse('@spekklez/foobar'), Ref(Package('spekklez', 'foobar'), None, None, None))
  assert_equals(parse('@spekklez/foobar@1.6.4'), Ref(Package('spekklez', 'foobar'), Selector(Version('1.6.4')), None, None))
  assert_equals(parse('@spekklez/foobar@>=1.6.4'), Ref(Package('spekklez', 'foobar'), Selector('>=1.6.4'), None, None))
  assert_equals(parse('spam@~1.0.0'), Ref(Package(None, 'spam'), Selector('~1.0.0'), None, None))
  assert_equals(parse('spam@~1.0.0/main'), Ref(Package(None, 'spam'), Selector('~1.0.0'), 'main', None))
  assert_equals(parse('spam@~1.0.0/main:run'), Ref(Package(None, 'spam'), Selector('~1.0.0'), 'main', 'run'))
  assert_equals(parse('spam@~1.0.0:run'), Ref(Package(None, 'spam'), Selector('~1.0.0'), None, 'run'))
  with assert_raises(ValueError):
    parse('.')
  with assert_raises(ValueError):
    parse('..')
  with assert_raises(ValueError):
    parse('/')
  with assert_raises(ValueError):
    parse('@/')
  with assert_raises(ValueError):
    parse('@')


def test_parse_package():
  with assert_raises(ValueError):
    parse_package('.')
  with assert_raises(ValueError):
    parse_package('..')
  with assert_raises(ValueError):
    parse_package('/')
  with assert_raises(ValueError):
    parse_package('@/')
  with assert_raises(ValueError):
    parse_package('@')
