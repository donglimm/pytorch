## @package scope
# Module caffe2.python.scope
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import threading
from past.builtins import basestring

from caffe2.proto import caffe2_pb2


# The name scope and device scope when creating a new operator.
_NAMESCOPE_SEPARATOR = '/'

_threadlocal_scope = threading.local()


def CurrentTags():
    """
    Return the current Tags context
    """
    global _threadlocal_scope
    if not hasattr(_threadlocal_scope, "tags"):
        _threadlocal_scope.tags = None
    return _threadlocal_scope.tags


def CurrentNameScope():
    global _threadlocal_scope
    if not hasattr(_threadlocal_scope, "namescope"):
        _threadlocal_scope.namescope = ''
    return _threadlocal_scope.namescope


def CurrentDeviceScope():
    global _threadlocal_scope
    if not hasattr(_threadlocal_scope, "devicescope"):
        _threadlocal_scope.devicescope = None
    return _threadlocal_scope.devicescope


@contextlib.contextmanager
def Tags(new_tags):
    """
    Defines the Tags context
    Arguments:
        new_tags: dict of string:string, defines the new context of Tags

    return:
        new Tags context, which merges current Tags context with the new new_tags
    """

    def _merge_tags(old_tags, new_tags):
        merged_new_tags = new_tags.copy()
        if old_tags is not None:
            for key, value in old_tags.items():
                if key in merged_new_tags:
                    if value != merged_new_tags[key]:
                        raise ValueError(
                            "Tags conflict detected: key {} has"
                            "old value {}, then gets a new value {}".format(
                                key, value, merged_new_tags[key]
                            )
                        )
                else:
                    merged_new_tags[key] = value
        return merged_new_tags

    global _threadlocal_scope
    assert isinstance(
        new_tags, dict
    ), "Tags takes in a dict of string:string as its argument."
    old_tags = CurrentTags()

    merged_new_tags = _merge_tags(old_tags, new_tags)
    _threadlocal_scope.tags = merged_new_tags
    try:
        yield
    finally:
        _threadlocal_scope.tags = old_tags


@contextlib.contextmanager
def NameScope(prefix, reset=False):
    global _threadlocal_scope
    assert isinstance(prefix, basestring) or prefix is None, \
        "NameScope takes in a string as its argument."
    old_scope = CurrentNameScope()
    prefix = prefix + _NAMESCOPE_SEPARATOR if prefix else ''
    if reset:
        _threadlocal_scope.namescope = prefix
    else:
        _threadlocal_scope.namescope = _threadlocal_scope.namescope + prefix

    try:
        yield
    finally:
        assert _threadlocal_scope.namescope.endswith(prefix), \
            "The namescope variable is changed from outside NameScope() calls."
        _threadlocal_scope.namescope = old_scope


@contextlib.contextmanager
def DeviceScope(scope, node_name=None):
    new_scope = caffe2_pb2.DeviceOption()
    if scope:
        assert isinstance(scope, caffe2_pb2.DeviceOption), \
            "DeviceScope takes in a caffe2_pb2.DeviceOption as its argument."
        new_scope.CopyFrom(scope)
    else:
        assert node_name, "At least one argument should be non-null in DeviceScope"

    # rewrite node_name if it is explicitly given
    if node_name:
        new_scope.node_name = node_name
    global _threadlocal_scope
    old_scope = CurrentDeviceScope()
    # nested scope should inherit the node_name if it is not explicitly set
    if old_scope and old_scope.HasField('node_name') and \
            not new_scope.HasField('node_name'):
        new_scope.node_name = old_scope.node_name
    _threadlocal_scope.devicescope = new_scope
    try:
        yield
    finally:
        assert _threadlocal_scope.devicescope == new_scope, \
            "The device scope is changed from outside DeviceScope() calls."
        _threadlocal_scope.devicescope = old_scope


@contextlib.contextmanager
def EmptyDeviceScope():
    """
    Allow users to 'disable' the device scope behaviour (so it can be
    controlled at a NetDef::DeviceOption level, not overridden at
    OperatorDef::DeviceOption level).

    This sets the CurrentDeviceScope() to None, so that the field is
    not set in CreateOperator(...), etc.
    """
    old_scope = CurrentDeviceScope()
    try:
        _threadlocal_scope.devicescope = None
        yield
    finally:
        _threadlocal_scope.devicescope = old_scope
        return
