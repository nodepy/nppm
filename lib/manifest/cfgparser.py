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

"""
Parser and evaluator for configuration filter strings.
"""

import io
import string
import nr.parsing.core as parsing


class _AstNode(object):

  def __str__(self):
    raise NotImplementedError

  def format(self, pretty=True):
    fp = io.StringIO()
    self.format_fp(fp, True)
    return fp.getvalue()

  def format_fp(self, fp, pretty=True, depth=0):
    attrs = ('{}={!r}'.format(k, getattr(self, k)) for k in self.__slots__)
    fp.write('{}({})'.format(type(self).__name__, ', '.join(attrs)))

  def eval(self, context):
    raise NotImplementedError


class Var(_AstNode):

  __slots__ = ('name',)

  def __init__(self, name):
    self.name = name

  def __str__(self):
    return self.name

  def eval(self, context):
    return context.isset(self.name)


class Logop(_AstNode):

  def __init__(self, left, op, right):
    assert op in ('and', 'or')
    self.left = left
    self.op = op
    self.right = right

  def __str__(self):
    return '{} {} {}'.format(self.left, type(self).__name__.lower(), self.right)

  def format_fp(self, fp, pretty=True, depth=0):
    indent = '  ' if pretty else ''
    nl = '\n' if pretty else ''
    sep = ',\n' if pretty else ', '
    fp.write('{}('.format(type(self).__name__) + nl)
    fp.write(indent * (depth+1) + 'left=')
    self.left.format_fp(fp, pretty, depth+2)
    fp.write(sep)
    fp.write(indent * (depth+1) + 'right=')
    self.right.format_fp(fp, pretty, depth+2)
    fp.write(nl + indent * depth + ')')

  def eval(self, context):
    a, b = self.left.eval(context), self.right.eval(context)
    if self.op == 'and':
      return a and b
    elif self.op == 'or':
      return a or b
    else:
      assert False, repr(self.op)


class Compare(_AstNode):

  OPERATORS = {
    '<': lambda a, b: a < b,
    '>': lambda a, b: a > b,
    '<=': lambda a, b: a <= b,
    '>=': lambda a, b: a >= b,
    '==': lambda a, b: a == b,
    '!=': lambda a, b: a != b
  }

  def __init__(self, name, op, value):
    assert op in self.OPERATORS
    self.name = name
    self.op = op
    self.value = value

  def __str__(self):
    return '{} {} {}'.format(self.name, self.op, self.value)

  def eval(self, context):
    try:
      a = context.getvalue(self.name)
    except KeyError as exc:
      return context.handle_eval_error(self, exc)
    try:
      b = context.coerce(type(a), self.value)
    except (TypeError, ValueError) as exc:
      return context.handle_eval_error(self, exc)
    return self.OPERATORS[self.op](a, b)


class Parser(object):
  """
  Parser for the configuration filter string.
  """

  alphanums = string.ascii_letters + string.digits
  value_chars = ''.join(set(chr(i) for i in range(32, 127)) - set('()<>=! '))

  rules = parsing.RuleSet(('eof', ''))
  rules.rule('', parsing.rules.regex_extract('[\t ]'), skip=True)
  rules.rule('(', parsing.rules.regex_extract(r'\('))
  rules.rule(')', parsing.rules.regex_extract(r'\)'))
  rules.rule('logop', parsing.rules.regex_extract(r'and'))
  rules.rule('logop', parsing.rules.regex_extract(r'or'))
  rules.rule('op', parsing.rules.regex_extract(r'=='))
  rules.rule('op', parsing.rules.regex_extract(r'!='))
  rules.rule('op', parsing.rules.regex_extract(r'<='))
  rules.rule('op', parsing.rules.regex_extract(r'>='))
  rules.rule('op', parsing.rules.regex_extract(r'<'))
  rules.rule('op', parsing.rules.regex_extract(r'>'))
  rules.rule('var', parsing.rules.regex_extract('[' + alphanums + ']+'))
  rules.rule('value', parsing.rules.regex_extract('[' + value_chars + ']+'))

  def __init__(self, source):
    self.scanner = parsing.Scanner(source)
    self.lexer = parsing.Tokenizer(self.rules, self.scanner)

  def parse(self):
    return self._parse_expression()

  def _parse_expression(self):
    token = self.lexer.next({'var', '('})
    if token.type == '(':
      op = self._parse_expression()
      self.lexer.next({')'})
      return op
    else:
      left = Var(token.value)
      while True:
        newop = self._parse_operator(left)
        if newop is None:
          break
        left = newop
    self.lexer.next({'eof'})
    return left

  def _parse_operator(self, left):
    assert isinstance(left, Var), type(left)
    token = self.lexer.next({'logop', 'op', 'eof'})  # .accept()?
    if not token:
      return None
    if token.type == 'logop':
      right = self._parse_expression()
      return Logop(left, token.value, right)
    elif token.type == 'op':
      value = self.lexer.next({'value'}).value  # weighted=True ?
      return Compare(left.name, token.value, value)


class Context(object):

  def __init__(self, vars, collect_errors=True):
    self.vars = vars
    self.coerce_handlers = {}
    self.collect_errors = collect_errors
    self.errors = []
    self.register_coercion(str, str)

  def defaults(self):
    self.register_coercion(int, int)
    self.register_coercion(float, float)

  def register_coercion(self, target_type, func):
    """
    Registers a handler function to coerce a string into *target_type*.
    """

    self.coerce_handlers[target_type] = func

  def isset(self, name):
    """
    Returns #True if the variable *name* is set.
    """

    return bool(self.vars.get(name))

  def getvalue(self, name):
    return self.vars[name]

  def coerce(self, target_type, value):
    if target_type not in self.coerce_handlers:
      raise TypeError('coerce to {} is not available'.format(target_type.__name__))
    return self.coerce_handlers[target_type](value)

  def handle_eval_error(self, node, exc):
    """
    Called when an error occurs during the evalation of a node. The default
    implementation raises an #EvalError. An alternative implementation may
    return a boolean value instead and ignore the error.
    """

    if self.collect_errors:
      self.errors.append(EvalError(node, exc))
      return False
    else:
      raise EvalError(node, exc)


class EvalError(Exception):

  def __init__(self, node, message):
    self.node = node
    self.message = message

  def __str__(self):
    return 'evaluation failed at "{}": {}'.format(self.node, self.message)


parse_cache = {}

def parse(s):
  s = s.strip()
  try:
    result = parse_cache[s]
  except KeyError:
    try:
      result = parse_cache[s] = Parser(s).parse()
    except parsing.UnexpectedTokenError:
      raise ValueError('invalid cfg-filter string: {!r}'.format(s))
  return result
