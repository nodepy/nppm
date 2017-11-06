
import functools
import threading

_finally_local = threading.local()

def finally_(push_func=None):
  """
  This decorator creates a new list for every call to the decorated function.
  Calling this function from inside the decorated function will push the
  *push_func* argument onto this newly created list. When the function returns
  or raises an exception, all items in this list are called.

  # Example

  ```python
  @finally_()
  def some_function():
    # ... do setup
    finally_(do_cleanup)
    # ... do stuff
  ```
  """

  if push_func is not None:
    _finally_local.stack[-1].append(push_func)
  else:
    def decorator(func):
      @functools.wraps(func)
      def wrapper(*args, **kwargs):
        if not hasattr(_finally_local, 'stack'):
          _finally_local.stack = []
        _finally_local.stack.append([])
        try:
          return func(*args, **kwargs)
        finally:
          for cleanup in _finally_local.stack.pop():
            cleanup()
      return wrapper
    return decorator
