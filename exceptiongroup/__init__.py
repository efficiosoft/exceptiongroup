"""Top-level package for exceptiongroup."""

import sys

from ._version import __version__

__all__ = ["ExceptionGroup", "split", "catch"]


class ExceptionGroup(BaseException):
    """An exception that contains other exceptions.

    Its main use is to represent the situation when multiple child tasks all
    raise errors "in parallel".

    Args:
      message (str): A description of the overall exception.
      exceptions (list): The exceptions.
      sources (list): For each exception, a string describing where it came
        from.

    Raises:
      TypeError: if any of the passed in objects are not instances of
          :exc:`BaseException`.
      ValueError: if the exceptions and sources lists don't have the same
          length.

    Handle the individual exceptions contained in a group like so::

        try:
            ...
        except ExceptionGroup as eg:
            for exc in eg.findall(ValueError):
                # Handle exc here
                eg = eg.remove(exc)
            exc = eg.find(TypeError)
            if exc:
                # Handle that as well
                eg = eg.remove(exc)
            eg.maybe_reraise()

    """

    def __init__(self, message, exceptions, sources):
        super().__init__(message, exceptions, sources)
        self.exceptions = list(exceptions)
        for exc in self.exceptions:
            if not isinstance(exc, BaseException):
                raise TypeError(
                    "Expected an exception object, not {!r}".format(exc)
                )
        self.message = message
        self.sources = list(sources)
        if len(self.sources) != len(self.exceptions):
            raise ValueError(
                "different number of sources ({}) and exceptions ({})".format(
                    len(self.sources), len(self.exceptions)
                )
            )

    def __bool__(self):
        return bool(self.exceptions)

    def __contains__(self, exception):
        return exception in self.exceptions

    # copy.copy doesn't work for ExceptionGroup, because BaseException have
    # rewrite __reduce_ex__ method.  We need to add __copy__ method to
    # make it can be copied.
    def __copy__(self):
        new_group = self.__class__(self.message, self.exceptions, self.sources)
        self._copy_magic_attrs(new_group)
        return new_group

    def __iter__(self):
        return zip(self.exceptions, self.sources)

    def __len__(self):
        return len(self.exceptions)

    def __str__(self):
        return ", ".join(repr(exc) for exc in self.exceptions)

    def __repr__(self):
        return "<ExceptionGroup: {}>".format(self)

    def _copy_magic_attrs(self, dst):
        """Copy exception-specific attributes to another :class:`ExceptionGroup`."""
        dst.__traceback__ = self.__traceback__
        dst.__context__ = self.__context__
        dst.__cause__ = self.__cause__
        # Setting __cause__ also implicitly sets the __suppress_context__
        # attribute to True.  So we should copy __suppress_context__ attribute
        # last, after copying __cause__.
        dst.__suppress_context__ = self.__suppress_context__

    def add(self, exception, source=""):
        """Return a new group with exceptions of this group + another exception.

        The magic attributes ``__cause__``, ``__context__``, ``__suppress_context__``
        and ``__traceback__`` are preserved.

        :param exception: exception to add
        :type  exception: BaseException
        :param source: string describing where the exception originated from
        :type  source: str
        :rtype: ExceptionGroup
        """
        new = type(self)(
            self.message,
            [*self.exceptions, exception],
            [*self.sources, source],
        )
        self._copy_magic_attrs(new)
        return new

    def find(self, predicate, with_source=False):
        """Return the first exception that fulfills some predicate or ``None``.

        :param predicate: see :meth:`findall`
        :type  predicate: callable, type, (type)
        :param with_source: see :meth:`findall`
        :type  with_source: bool
        :rtype: BaseException, None
        """
        for item in self.findall(predicate, with_source):
            return item

    def findall(self, predicate, with_source=False):
        """Yield only exceptions that fulfill some predicate.

        :param predicate:
            Callable that takes a :class:`BaseException` object and returns whether it
            fulfills some criteria (``True``) or not (``False``).
            If a type or tuple of types is given instead of a callable, :func:`isinstance`
            is automatically used as the predicate function.
        :type  predicate: callable, type, (type)
        :param with_source:
            Normally, only the matching :class:`BaseException` objects are
            yielded. However, when this is set to ``True``, two-element tuples are
            yielded whose first element is the :class:`BaseException` and the second
            is the associated source (:class:`str`).
        :type  with_source: bool
        """
        if isinstance(predicate, (type, tuple)):
            exc_type = predicate
            predicate = lambda _exc: isinstance(_exc, exc_type)
        if with_source:
            for exception, source in zip(self.exceptions, self.sources):
                if predicate(exception):
                    yield exception, source
        else:
            yield from filter(predicate, self.exceptions)

    def maybe_reraise(self, from_exception=0, unwrap=True):
        """(Re-)raise this exception group if it contains any exception.

        If the group is empty, this returns without doing anything.

        :param from_exception:
            This has the same meaning as the ``from`` keyword of the ``raise``
            statement. The default value of ``0`` causes the exception originally
            caught by the current ``except`` block to be used. This is retrieved using
            ``sys.exc_info()[1]``.
        :type  from_exception: BaseException, None
        :param unwrap:
            Normally, when there is just one exception left in the group, it is
            unwrapped and raised as is. With this option, you can prevent the
            unwrapping.
        :type  unwrap: bool
        """
        if not self.exceptions:
            return
        if unwrap and len(self.exceptions) == 1:
            exc = self.exceptions[0]
        else:
            exc = self
        if from_exception == 0:
            from_exception = sys.exc_info()[1]
        raise exc from from_exception

    def remove(self, exception):
        """Return a new group without a particular exception.

        The magic attributes ``__cause__``, ``__context__``, ``__suppress_context__``
        and ``__traceback__`` are preserved.

        :param exception: exception to remove
        :type  exception: BaseException
        :rtype: ExceptionGroup
        :raises ValueError: if exception not contained in this group
        """
        try:
            idx = self.exceptions.index(exception)
        except ValueError:
            raise ValueError(
                "{!r} not contained in {!r}".format(exception, self)
            ) from None
        new = type(self)(
            self.message,
            [*self.exceptions[:idx], *self.exceptions[idx + 1 :]],
            [*self.sources[:idx], *self.sources[idx + 1 :]],
        )
        self._copy_magic_attrs(new)
        return new


from . import _monkeypatch
from ._tools import split, catch
