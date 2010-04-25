# errors.py -- errors for dulwich
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
# Copyright (C) 2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# or (at your option) any later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

"""Dulwich-related exception classes and utility functions."""

import binascii


class ChecksumMismatch(Exception):
    """A checksum didn't match the expected contents."""

    def __init__(self, expected, got, extra=None):
        if len(expected) == 20:
            expected = binascii.hexlify(expected)
        if len(got) == 20:
            got = binascii.hexlify(got)
        self.expected = expected
        self.got = got
        self.extra = extra
        if self.extra is None:
            Exception.__init__(self,
                "Checksum mismatch: Expected %s, got %s" % (expected, got))
        else:
            Exception.__init__(self,
                "Checksum mismatch: Expected %s, got %s; %s" %
                (expected, got, extra))


class WrongObjectException(Exception):
    """Baseclass for all the _ is not a _ exceptions on objects.

    Do not instantiate directly.

    Subclasses should define a type_name attribute that indicates what
    was expected if they were raised.
    """

    def __init__(self, sha, *args, **kwargs):
        Exception.__init__(self, "%s is not a %s" % (sha, self.type_name))


class NotCommitError(WrongObjectException):
    """Indicates that the sha requested does not point to a commit."""

    type_name = 'commit'


class NotTreeError(WrongObjectException):
    """Indicates that the sha requested does not point to a tree."""

    type_name = 'tree'


class NotTagError(WrongObjectException):
    """Indicates that the sha requested does not point to a tag."""

    type_name = 'tag'


class NotBlobError(WrongObjectException):
    """Indicates that the sha requested does not point to a blob."""

    type_name = 'blob'


class MissingCommitError(Exception):
    """Indicates that a commit was not found in the repository"""

    def __init__(self, sha, *args, **kwargs):
        Exception.__init__(self, "%s is not in the revision store" % sha)


class ObjectMissing(Exception):
    """Indicates that a requested object is missing."""

    def __init__(self, sha, *args, **kwargs):
        Exception.__init__(self, "%s is not in the pack" % sha)


class ApplyDeltaError(Exception):
    """Indicates that applying a delta failed."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class NotGitRepository(Exception):
    """Indicates that no Git repository was found."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class GitProtocolError(Exception):
    """Git protocol exception."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class HangupException(GitProtocolError):
    """Hangup exception."""

    def __init__(self):
        Exception.__init__(self,
            "The remote server unexpectedly closed the connection.")


class FileFormatException(Exception):
    """Base class for exceptions relating to reading git file formats."""


class PackedRefsException(FileFormatException):
    """Indicates an error parsing a packed-refs file."""


class ObjectFormatException(FileFormatException):
    """Indicates an error parsing an object."""


class NoIndexPresent(Exception):
    """No index is present."""
