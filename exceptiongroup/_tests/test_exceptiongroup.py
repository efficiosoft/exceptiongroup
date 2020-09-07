import copy
import pytest

from exceptiongroup import ExceptionGroup


def raise_group():
    try:
        1 / 0
    except Exception as e:
        raise ExceptionGroup("ManyError", [e], [str(e)]) from e


def test_exception_group_init():
    memberA = ValueError("A")
    memberB = RuntimeError("B")
    group = ExceptionGroup(
        "many error.", [memberA, memberB], [str(memberA), str(memberB)]
    )
    assert group.exceptions == [memberA, memberB]
    assert group.message == "many error."
    assert group.sources == [str(memberA), str(memberB)]
    assert group.args == (
        "many error.",
        [memberA, memberB],
        [str(memberA), str(memberB)],
    )


def test_exception_group_when_members_are_not_exceptions():
    with pytest.raises(TypeError):
        ExceptionGroup(
            "error",
            [RuntimeError("RuntimeError"), "error2"],
            ["RuntimeError", "error2"],
        )


def test_exception_group_init_when_exceptions_messages_not_equal():
    with pytest.raises(ValueError):
        ExceptionGroup(
            "many error.", [ValueError("A"), RuntimeError("B")], ["A"]
        )


def test_exception_group_bool():
    assert bool(ExceptionGroup("E", [], [])) is False
    assert bool(ExceptionGroup("E", [ValueError()], [""])) is True


def test_exception_group_contains():
    err = ValueError()
    group = ExceptionGroup("E", [err], [""])
    assert err in group
    assert ValueError() not in group


def test_exception_group_find():
    err = ValueError()
    group = ExceptionGroup("E", [err], [""])
    assert group.find(ValueError) is err
    assert group.find(TypeError) is None


def test_exception_group_find_callable_predicate():
    err = ValueError()
    group = ExceptionGroup("E", [err], [""])
    predicate1 = lambda e: e is err
    assert group.find(predicate1) is err
    predicate2 = lambda _: False
    assert group.find(predicate2) is None


def test_exception_group_find_with_source():
    err = ValueError()
    group = ExceptionGroup("E", [err], ["x"])
    assert group.find(ValueError, with_source=True) == (err, "x")
    assert group.find(TypeError, with_source=True) is None


def test_exception_group_findall():
    err1 = ValueError()
    err2 = TypeError()
    group = ExceptionGroup("E", [err1, err2], ["", ""])
    assert tuple(group.findall(ValueError)) == (err1,)
    assert tuple(group.findall((ValueError, TypeError))) == (err1, err2)


def test_exception_group_iter():
    err1 = ValueError()
    err2 = ValueError()
    group = ExceptionGroup("E", [err1, err2], ["", ""])
    assert tuple(group) == ((err1, ""), (err2, ""))


def test_exception_group_len():
    assert len(ExceptionGroup("E", [], [])) == 0
    assert len(ExceptionGroup("E", [ValueError()], [""])) == 1


def test_exception_group_maybe_reraise_empty():
    group = ExceptionGroup("E", [], [])
    group.maybe_reraise()


def test_exception_group_maybe_reraise_unwrap():
    err = ValueError()
    group = ExceptionGroup("E", [err], [""])
    try:
        group.maybe_reraise()
    except ValueError as caught_err:
        assert caught_err is err
    try:
        group.maybe_reraise(unwrap=False)
    except ExceptionGroup as caught_err:
        assert caught_err is group


def test_exception_group_maybe_reraise_from_exception():
    err = ValueError()
    try:
        raise_group()
    except ExceptionGroup as group1:
        group2 = ExceptionGroup("E", [err], [""])
        try:
            group2.maybe_reraise()
        except ValueError as caught_err:
            assert caught_err.__cause__ is group1
    try:
        raise_group()
    except ExceptionGroup as group1:
        group2 = ExceptionGroup("E", [err], [""])
        err2 = TypeError()
        try:
            group2.maybe_reraise(from_exception=err2)
        except ValueError as caught_err:
            assert caught_err.__cause__ is err2


def test_exception_group_str():
    memberA = ValueError("memberA")
    memberB = ValueError("memberB")
    group = ExceptionGroup(
        "many error.", [memberA, memberB], [str(memberA), str(memberB)]
    )
    assert "memberA" in str(group)
    assert "memberB" in str(group)

    assert "ExceptionGroup: " in repr(group)
    assert "memberA" in repr(group)
    assert "memberB" in repr(group)


def test_exception_group_copy():
    try:
        raise_group()  # the exception is raise by `raise...from..`
    except ExceptionGroup as e:
        group = e

    another_group = copy.copy(group)
    assert another_group.message == group.message
    assert another_group.exceptions == group.exceptions
    assert another_group.sources == group.sources
    assert another_group.__traceback__ is group.__traceback__
    assert another_group.__cause__ is group.__cause__
    assert another_group.__context__ is group.__context__
    assert another_group.__suppress_context__ is group.__suppress_context__
    assert another_group.__cause__ is not None
    assert another_group.__context__ is not None
    assert another_group.__suppress_context__ is True

    # doing copy when __suppress_context__ is False
    group.__suppress_context__ = False
    another_group = copy.copy(group)
    assert another_group.__cause__ is group.__cause__
    assert another_group.__context__ is group.__context__
    assert another_group.__suppress_context__ is group.__suppress_context__
    assert another_group.__suppress_context__ is False
