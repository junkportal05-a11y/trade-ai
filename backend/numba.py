"""
Mock numba module to allow running packages (like pandas-ta) on Python 3.14
where numba cannot be compiled or installed yet.
"""


def njit(*args, **kwargs):
    if len(args) == 1 and callable(args[0]):
        return args[0]

    def decorator(func):
        return func

    return decorator


# Add other decorators if needed by pandas-ta
jit = njit
prange = range
