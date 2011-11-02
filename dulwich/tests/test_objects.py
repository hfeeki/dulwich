# test_objects.py -- tests for objects.py
# Copyright (C) 2007 James Westby <jw+debian@jameswestby.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your option) any later version of
# the License.
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

"""Tests for git base objects."""

# TODO: Round-trip parse-serialize-parse and serialize-parse-serialize tests.


from io import BytesIO
import datetime
import os
import stat
import warnings
import binascii

from dulwich.errors import (
    ObjectFormatException,
    )
from dulwich._compat import (
    permutations,
    )
from dulwich.objects import (
    Blob,
    Tree,
    Commit,
    ShaFile,
    Tag,
    format_timezone,
    hex_to_sha,
    sha_to_hex,
    hex_to_filename,
    check_hexsha,
    check_identity,
    parse_timezone,
    TreeEntry,
    parse_tree,
    _parse_tree_py,
    sorted_tree_items,
    _sorted_tree_items_py,
    )
from dulwich.tests import (
    TestCase,
    )
from .utils import (
    make_commit,
    make_object,
    functest_builder,
    ext_functest_builder,
    )

from dulwich.py3k import *

a_sha = b'6f670c0fb53f9463760b7295fbb814e965fb20c8'
b_sha = b'2969be3e8ee1c0222396a5611407e4769f14e54b'
c_sha = b'954a536f7819d40e6f637f849ee187dd10066349'
tree_sha = b'70c190eb48fa8bbb50ddc692a17b44cb781af7f6'
tag_sha = b'71033db03a03c6a36721efcf1968dd8f8e0cf023'


class TestHexToSha(TestCase):

    def test_simple(self):
        self.assertEqual(b"\xab\xcd" * 10, hex_to_sha("abcd" * 10))

    def test_reverse(self):
        self.assertEqual("abcd" * 10, sha_to_hex(b"\xab\xcd" * 10))


class BlobReadTests(TestCase):
    """Test decompression of blobs"""

    def get_sha_file(self, cls, base, sha):
        dir = os.path.join(os.path.dirname(__file__), 'data', base)
        return cls.from_path(hex_to_filename(dir, sha))

    def get_blob(self, sha):
        """Return the blob named sha from the test data dir"""
        return self.get_sha_file(Blob, 'blobs', sha)

    def get_tree(self, sha):
        return self.get_sha_file(Tree, 'trees', sha)

    def get_tag(self, sha):
        return self.get_sha_file(Tag, 'tags', sha)

    def commit(self, sha):
        return self.get_sha_file(Commit, 'commits', sha)

    def test_decompress_simple_blob(self):
        b = self.get_blob(a_sha)
        self.assertEqual(b.data, b'test 1\n')
        self.assertEqual(convert3kstr(b.sha().hexdigest(), BYTES), a_sha)

    def test_hash(self):
        b = self.get_blob(a_sha)
        self.assertEqual(hash(b.id), hash(b))

    def test_parse_empty_blob_object(self):
        sha = b'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'
        b = self.get_blob(sha)
        self.assertEqual(b.data, b'')
        self.assertEqual(b.id, sha)
        self.assertEqual(convert3kstr(b.sha().hexdigest(), BYTES), sha)

    def test_create_blob_from_string(self):
        string = b'test 2\n'
        b = Blob.from_string(string)
        self.assertEqual(b.data, string)
        self.assertEqual(convert3kstr(b.sha().hexdigest(), BYTES), b_sha)

    def test_legacy_from_file(self):
        b1 = Blob.from_string("foo")
        b_raw = b1.as_legacy_object()
        b2 = b1.from_file(BytesIO(b_raw))
        self.assertEqual(b1, b2)

    def test_chunks(self):
        string = b'test 5\n'
        b = Blob.from_string(string)
        self.assertEqual([string], b.chunked)

    def test_set_chunks(self):
        b = Blob()
        b.chunked = ['te', 'st', ' 5\n']
        self.assertEqual(b'test 5\n', b.data)
        b.chunked = ['te', 'st', ' 6\n']
        self.assertEqual(b'test 6\n', b.as_raw_string())

    def test_parse_legacy_blob(self):
        string = b'test 3\n'
        b = self.get_blob(c_sha)
        self.assertEqual(b.data, string)
        self.assertEqual(convert3kstr(b.sha().hexdigest(), BYTES), c_sha)

    def test_eq(self):
        blob1 = self.get_blob(a_sha)
        blob2 = self.get_blob(a_sha)
        self.assertEqual(blob1, blob2)

    def test_read_tree_from_file(self):
        t = self.get_tree(tree_sha)
        self.assertEqual(list(t.items())[0], ('a', 33188, a_sha))
        self.assertEqual(list(t.items())[1], ('b', 33188, b_sha))

    def test_read_tag_from_file(self):
        t = self.get_tag(tag_sha)
        self.assertEqual(t.object, (Commit, b'51b668fd5bf7061b7d6fa525f88803e6cfadaa51'))
        self.assertEqual(t.name,b'signed')
        self.assertEqual(t.tagger,'Ali Sabil <ali.sabil@gmail.com>')
        self.assertEqual(t.tag_time, 1231203091)
        self.assertEqual(t.message, 'This is a signed tag\n-----BEGIN PGP SIGNATURE-----\nVersion: GnuPG v1.4.9 (GNU/Linux)\n\niEYEABECAAYFAkliqx8ACgkQqSMmLy9u/kcx5ACfakZ9NnPl02tOyYP6pkBoEkU1\n5EcAn0UFgokaSvS371Ym/4W9iJj6vh3h\n=ql7y\n-----END PGP SIGNATURE-----\n')

    def test_read_commit_from_file(self):
        sha = b'60dacdc733de308bb77bb76ce0fb0f9b44c9769e'
        c = self.commit(sha)
        self.assertEqual(c.tree, tree_sha)
        self.assertEqual(c.parents,
            [b'0d89f20333fbb1d2f3a94da77f4981373d8f4310'])
        self.assertEqual(c.author,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.committer,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.commit_time, 1174759230)
        self.assertEqual(c.commit_timezone, 0)
        self.assertEqual(c.author_timezone, 0)
        self.assertEqual(c.message, 'Test commit\n')

    def test_read_commit_no_parents(self):
        sha = b'0d89f20333fbb1d2f3a94da77f4981373d8f4310'
        c = self.commit(sha)
        self.assertEqual(c.tree, b'90182552c4a85a45ec2a835cadc3451bebdfe870')
        self.assertEqual(c.parents, [])
        self.assertEqual(c.author,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.committer,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.commit_time, 1174758034)
        self.assertEqual(c.commit_timezone, 0)
        self.assertEqual(c.author_timezone, 0)
        self.assertEqual(c.message, 'Test commit\n')

    def test_read_commit_two_parents(self):
        sha = '5dac377bdded4c9aeb8dff595f0faeebcc8498cc'
        c = self.commit(sha)
        self.assertEqual(c.tree, b'd80c186a03f423a81b39df39dc87fd269736ca86')
        self.assertEqual(c.parents, [b'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                                       b'4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'])
        self.assertEqual(c.author,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.committer,
            'James Westby <jw+debian@jameswestby.net>')
        self.assertEqual(c.commit_time, 1174773719)
        self.assertEqual(c.commit_timezone, 0)
        self.assertEqual(c.author_timezone, 0)
        self.assertEqual(c.message, 'Merge ../b\n')

    def test_stub_sha(self):
        sha = b'5' * 40
        c = make_commit(id=sha, message='foo')
        self.assertTrue(isinstance(c, Commit))
        self.assertEqual(sha, c.id)
        self.assertNotEqual(sha, c._make_sha())


class ShaFileCheckTests(TestCase):

    def assertCheckFails(self, cls, data):
        obj = cls()
        def do_check():
            obj.set_raw_string(data)
            obj.check()
        self.assertRaises(ObjectFormatException, do_check)

    def assertCheckSucceeds(self, cls, data):
        obj = cls()
        obj.set_raw_string(data)
        self.assertEqual(None, obj.check())


small_buffer_zlib_object = (
 "\x48\x89\x15\xcc\x31\x0e\xc2\x30\x0c\x40\x51\xe6"
 "\x9c\xc2\x3b\xaa\x64\x37\xc4\xc1\x12\x42\x5c\xc5"
 "\x49\xac\x52\xd4\x92\xaa\x78\xe1\xf6\x94\xed\xeb"
 "\x0d\xdf\x75\x02\xa2\x7c\xea\xe5\x65\xd5\x81\x8b"
 "\x9a\x61\xba\xa0\xa9\x08\x36\xc9\x4c\x1a\xad\x88"
 "\x16\xba\x46\xc4\xa8\x99\x6a\x64\xe1\xe0\xdf\xcd"
 "\xa0\xf6\x75\x9d\x3d\xf8\xf1\xd0\x77\xdb\xfb\xdc"
 "\x86\xa3\x87\xf1\x2f\x93\xed\x00\xb7\xc7\xd2\xab"
 "\x2e\xcf\xfe\xf1\x3b\x50\xa4\x91\x53\x12\x24\x38"
 "\x23\x21\x86\xf0\x03\x2f\x91\x24\x52"
 )


class ShaFileTests(TestCase):

    def test_deflated_smaller_window_buffer(self):
        # zlib on some systems uses smaller buffers,
        # resulting in a different header.
        # See https://github.com/libgit2/libgit2/pull/464
        sf = ShaFile.from_file(StringIO(small_buffer_zlib_object))
        self.assertEquals(sf.type_name, "tag")
        self.assertEquals(sf.tagger, " <@localhost>")


class CommitSerializationTests(TestCase):

    def make_commit(self, **kwargs):
        attrs = {'tree': b'd80c186a03f423a81b39df39dc87fd269736ca86',
                 'parents': [b'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                             b'4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'],
                 'author': 'James Westby <jw+debian@jameswestby.net>',
                 'committer': 'James Westby <jw+debian@jameswestby.net>',
                 'commit_time': 1174773719,
                 'author_time': 1174773719,
                 'commit_timezone': 0,
                 'author_timezone': 0,
                 'message':  'Merge ../b\n'}
        attrs.update(kwargs)
        return make_commit(**attrs)

    def test_encoding(self):
        c = self.make_commit(encoding='iso8859-1')
        self.assertTrue(b'encoding iso8859-1\n' in c.as_raw_string())

    def test_short_timestamp(self):
        c = self.make_commit(commit_time=30)
        c1 = Commit()
        c1.set_raw_string(c.as_raw_string())
        self.assertEqual(30, c1.commit_time)

    def test_raw_length(self):
        c = self.make_commit()
        self.assertEqual(len(c.as_raw_string()), c.raw_length())

    def test_simple(self):
        c = self.make_commit()
        self.assertEqual(c.id, b'5dac377bdded4c9aeb8dff595f0faeebcc8498cc')
        self.assertEqual(
                b'tree d80c186a03f423a81b39df39dc87fd269736ca86\n'
                b'parent ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd\n'
                b'parent 4cffe90e0a41ad3f5190079d7c8f036bde29cbe6\n'
                b'author James Westby <jw+debian@jameswestby.net> '
                b'1174773719 +0000\n'
                b'committer James Westby <jw+debian@jameswestby.net> '
                b'1174773719 +0000\n'
                b'\n'
                b'Merge ../b\n', c.as_raw_string())

    def test_timezone(self):
        c = self.make_commit(commit_timezone=(5 * 60))
        self.assertTrue(b" +0005\n" in c.as_raw_string())

    def test_neg_timezone(self):
        c = self.make_commit(commit_timezone=(-1 * 3600))
        self.assertTrue(b" -0100\n" in c.as_raw_string())


default_committer = 'James Westby <jw+debian@jameswestby.net> 1174773719 +0000'

class CommitParseTests(ShaFileCheckTests):

    def make_commit_lines(self,
                          tree=b'd80c186a03f423a81b39df39dc87fd269736ca86',
                          parents=[b'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                                   b'4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'],
                          author=default_committer,
                          committer=default_committer,
                          encoding=None,
                          message='Merge ../b\n',
                          extra=None):
        lines = []
        if tree is not None:
            lines.append(b'tree ' + tree)
        if parents is not None:
            lines.extend(b'parent ' + p for p in parents)
        if author is not None:
            lines.append(b'author ' + convert3kstr(author, BYTES))
        if committer is not None:
            lines.append(b'committer ' + convert3kstr(committer, BYTES))
        if encoding is not None:
            lines.append(b'encoding ' + convert3kstr(encoding, BYTES))
        if extra is not None:
            for name, value in sorted(extra.items()):
                lines.append(convert3kstr(name, BYTES) + b' ' + convert3kstr(value, BYTES))
        lines.append(b'')
        if message is not None:
            lines.append(convert3kstr(message, BYTES))
        return lines

    def make_commit_text(self, **kwargs):
        return b'\n'.join(self.make_commit_lines(**kwargs))

    def test_simple(self):
        c = Commit.from_string(self.make_commit_text())
        self.assertEqual('Merge ../b\n', c.message)
        self.assertEqual('James Westby <jw+debian@jameswestby.net>', c.author)
        self.assertEqual('James Westby <jw+debian@jameswestby.net>',
                          c.committer)
        self.assertEqual(b'd80c186a03f423a81b39df39dc87fd269736ca86', c.tree)
        self.assertEqual([b'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                           b'4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'],
                          c.parents)
        expected_time = datetime.datetime(2007, 3, 24, 22, 1, 59)
        self.assertEqual(expected_time,
                          datetime.datetime.utcfromtimestamp(c.commit_time))
        self.assertEqual(0, c.commit_timezone)
        self.assertEqual(expected_time,
                          datetime.datetime.utcfromtimestamp(c.author_time))
        self.assertEqual(0, c.author_timezone)
        self.assertEqual(None, c.encoding)

    def test_custom(self):
        c = Commit.from_string(self.make_commit_text(
          extra={b'extra-field': b'data'}))
        self.assertEqual([(b'extra-field', b'data')], c.extra)

    def test_encoding(self):
        c = Commit.from_string(self.make_commit_text(encoding='UTF-8'))
        self.assertEqual('UTF-8', c.encoding)

    def test_check(self):
        self.assertCheckSucceeds(Commit, self.make_commit_text())
        self.assertCheckSucceeds(Commit, self.make_commit_text(parents=None))
        self.assertCheckSucceeds(Commit,
                                 self.make_commit_text(encoding='UTF-8'))

        self.assertCheckFails(Commit, self.make_commit_text(tree=b'xxx'))
        self.assertCheckFails(Commit, self.make_commit_text(
          parents=[a_sha, b'xxx']))
        bad_committer = "some guy without an email address 1174773719 +0000"
        self.assertCheckFails(Commit,
                              self.make_commit_text(committer=bad_committer))
        self.assertCheckFails(Commit,
                              self.make_commit_text(author=bad_committer))
        self.assertCheckFails(Commit, self.make_commit_text(author=None))
        self.assertCheckFails(Commit, self.make_commit_text(committer=None))
        self.assertCheckFails(Commit, self.make_commit_text(
          author=None, committer=None))

    def test_check_duplicates(self):
        # duplicate each of the header fields
        for i in range(5):
            lines = self.make_commit_lines(parents=[a_sha], encoding='UTF-8')
            lines.insert(i, lines[i])
            text = b'\n'.join(lines)
            if lines[i].startswith(b'parent'):
                # duplicate parents are ok for now
                self.assertCheckSucceeds(Commit, text)
            else:
                self.assertCheckFails(Commit, text)

    def test_check_order(self):
        lines = self.make_commit_lines(parents=[a_sha], encoding='UTF-8')
        headers = lines[:5]
        rest = lines[5:]
        # of all possible permutations, ensure only the original succeeds
        for perm in permutations(headers):
            perm = list(perm)
            text = b'\n'.join(perm + rest)
            if perm == headers:
                self.assertCheckSucceeds(Commit, text)
            else:
                self.assertCheckFails(Commit, text)


_TREE_ITEMS = {
  b'a.c': (0o100755, b'd80c186a03f423a81b39df39dc87fd269736ca86'),
  b'a': (stat.S_IFDIR, b'd80c186a03f423a81b39df39dc87fd269736ca86'),
  b'a/c': (stat.S_IFDIR, b'd80c186a03f423a81b39df39dc87fd269736ca86'),
  }

_SORTED_TREE_ITEMS = [
  TreeEntry('a.c', 0o100755, b'd80c186a03f423a81b39df39dc87fd269736ca86'),
  TreeEntry('a', stat.S_IFDIR, b'd80c186a03f423a81b39df39dc87fd269736ca86'),
  TreeEntry('a/c', stat.S_IFDIR, b'd80c186a03f423a81b39df39dc87fd269736ca86'),
  ]


class TreeTests(ShaFileCheckTests):

    def test_add(self):
        myhexsha = b"d80c186a03f423a81b39df39dc87fd269736ca86"
        x = Tree()
        x.add(b"myname", 0o100755, myhexsha)
        self.assertEqual(x[b"myname"], (0o100755, myhexsha))
        self.assertEqual(b'100755 myname\0' + hex_to_sha(myhexsha),
                x.as_raw_string(), BYTES)

    def test_add_old_order(self):
        myhexsha = b"d80c186a03f423a81b39df39dc87fd269736ca86"
        x = Tree()
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            x.add(0o100755, b"myname", myhexsha)
        finally:
            warnings.resetwarnings()
        self.assertEqual(x[b"myname"], (0o100755, myhexsha))
        self.assertEqual(b'100755 myname\0' + hex_to_sha(myhexsha),
                x.as_raw_string())

    def test_simple(self):
        myhexsha = b"d80c186a03f423a81b39df39dc87fd269736ca86"
        x = Tree()
        x["myname"] = (0o100755, myhexsha)
        self.assertEqual(b'100755 myname\0' + hex_to_sha(myhexsha),
                x.as_raw_string())

    def test_tree_update_id(self):
        x = Tree()
        x["a.c"] = (0o100755, b"d80c186a03f423a81b39df39dc87fd269736ca86")
        self.assertEqual(b"0c5c6bc2c081accfbc250331b19e43b904ab9cdd", x.id)
        x["a.b"] = (stat.S_IFDIR, b"d80c186a03f423a81b39df39dc87fd269736ca86")
        self.assertEqual(b"07bfcb5f3ada15bbebdfa3bbb8fd858a363925c8", x.id)

    def test_tree_iteritems_dir_sort(self):
        x = Tree()
        for name, item in _TREE_ITEMS.items():
            x[name] = item
        self.assertEqual(_SORTED_TREE_ITEMS, list(x.items()))

    def test_tree_items_dir_sort(self):
        x = Tree()
        for name, item in _TREE_ITEMS.items():
            x[name] = item
        self.assertEqual(_SORTED_TREE_ITEMS, list(x.items()))

    def _do_test_parse_tree(self, parse_tree):
        dir = os.path.join(os.path.dirname(__file__), 'data', 'trees')
        o = Tree.from_path(hex_to_filename(dir, tree_sha))
        self.assertEqual([(b'a', 0o100644, a_sha), (b'b', 0o100644, b_sha)],
                          list(parse_tree(o.as_raw_string())))
        # test a broken tree that has a leading 0 on the file mode
        broken_tree = b'0100644 foo\0' + hex_to_sha(a_sha)

        def eval_parse_tree(*args, **kwargs):
            return list(parse_tree(*args, **kwargs))

        self.assertEqual([(b'foo', 0o100644, a_sha)],
                          eval_parse_tree(broken_tree))
        self.assertRaises(ObjectFormatException,
                          eval_parse_tree, broken_tree, strict=True)

    test_parse_tree = functest_builder(_do_test_parse_tree, _parse_tree_py)
    test_parse_tree_extension = ext_functest_builder(_do_test_parse_tree,
                                                     parse_tree)

    def _do_test_sorted_tree_items(self, sorted_tree_items):
        def do_sort(entries):
            return list(sorted_tree_items(entries, False))

        actual = do_sort(_TREE_ITEMS)
        self.assertEqual(_SORTED_TREE_ITEMS, actual)
        self.assertTrue(isinstance(actual[0], TreeEntry))

        # C/Python implementations may differ in specific error types, but
        # should all error on invalid inputs.
        # For example, the C implementation has stricter type checks, so may
        # raise TypeError where the Python implementation raises AttributeError.
        errors = (TypeError, ValueError, AttributeError)
        self.assertRaises(errors, do_sort, 'foo')
        self.assertRaises(errors, do_sort, {'foo': (1, 2, 3)})

        myhexsha = b'd80c186a03f423a81b39df39dc87fd269736ca86'
        self.assertRaises(errors, do_sort, {'foo': ('xxx', myhexsha)})
        self.assertRaises(errors, do_sort, {'foo': (0o100755, 12345)})

    test_sorted_tree_items = functest_builder(_do_test_sorted_tree_items,
                                              _sorted_tree_items_py)
    test_sorted_tree_items_extension = ext_functest_builder(
      _do_test_sorted_tree_items, sorted_tree_items)

    def _do_test_sorted_tree_items_name_order(self, sorted_tree_items):
        self.assertEqual([
          TreeEntry('a', stat.S_IFDIR,
                    b'd80c186a03f423a81b39df39dc87fd269736ca86'),
          TreeEntry('a.c', 0o100755, b'd80c186a03f423a81b39df39dc87fd269736ca86'),
          TreeEntry('a/c', stat.S_IFDIR,
                    b'd80c186a03f423a81b39df39dc87fd269736ca86'),
          ], list(sorted_tree_items(_TREE_ITEMS, True)))

    test_sorted_tree_items_name_order = functest_builder(
      _do_test_sorted_tree_items_name_order, _sorted_tree_items_py)
    test_sorted_tree_items_name_order_extension = ext_functest_builder(
      _do_test_sorted_tree_items_name_order, sorted_tree_items)

    def test_check(self):
        t = Tree
        sha = hex_to_sha(a_sha)

        # filenames
        self.assertCheckSucceeds(t, b'100644 .a\0' + sha)
        self.assertCheckFails(t, b'100644 \0' + sha)
        self.assertCheckFails(t, b'100644 .\0' + sha)
        self.assertCheckFails(t, b'100644 a/a\0' + sha)
        self.assertCheckFails(t, b'100644 ..\0' + sha)

        # modes
        self.assertCheckSucceeds(t, b'100644 a\0' + sha)
        self.assertCheckSucceeds(t, b'100755 a\0' + sha)
        self.assertCheckSucceeds(t, b'160000 a\0' + sha)
        # TODO more whitelisted modes
        self.assertCheckFails(t, b'123456 a\0' + sha)
        self.assertCheckFails(t, b'123abc a\0' + sha)
        # should fail check, but parses ok
        self.assertCheckFails(t, b'0100644 foo\0' + sha)

        # shas
        self.assertCheckFails(t, b'100644 a\0' + convert3kstr('x' * 5, BYTES))
        self.assertCheckFails(t, b'100644 a\0' + convert3kstr('x' * 18 + '\0', BYTES))
        self.assertCheckFails(t, b'100644 a\0' + convert3kstr('x' * 21, BYTES) + b'\n100644 b\0' + sha)

        # ordering
        sha2 = hex_to_sha(b_sha)
        self.assertCheckSucceeds(t, b'100644 a\0' + sha + b'\n100644 b\0' + sha)
        self.assertCheckSucceeds(t, b'100644 a\0' + sha + b'\n100644 b\0' + sha2)
        self.assertCheckFails(t, b'100644 a\0' + sha + b'\n100755 a\0' + sha2)
        self.assertCheckFails(t, b'100644 b\0' + sha2 + b'\n100644 a\0' + sha)

    def test_iter(self):
        t = Tree()
        t[b"foo"] = (0o100644, a_sha)
        self.assertEqual(set([b"foo"]), set(t))


class TagSerializeTests(TestCase):

    def test_serialize_simple(self):
        x = make_object(Tag,
                        tagger='Jelmer Vernooij <jelmer@samba.org>',
                        name='0.1',
                        message='Tag 0.1',
                        object=(Blob, b'd80c186a03f423a81b39df39dc87fd269736ca86'),
                        tag_time=423423423,
                        tag_timezone=0)
        self.assertEqual((b'object d80c186a03f423a81b39df39dc87fd269736ca86\n'
                           b'type blob\n'
                           b'tag 0.1\n'
                           b'tagger Jelmer Vernooij <jelmer@samba.org> '
                           b'423423423 +0000\n'
                           b'\n'
                           b'Tag 0.1'), x.as_raw_string())


default_tagger = ('Linus Torvalds <torvalds@woody.linux-foundation.org> '
                  '1183319674 -0700')
default_message = """Linux 2.6.22-rc7
-----BEGIN PGP SIGNATURE-----
Version: GnuPG v1.4.7 (GNU/Linux)

iD8DBQBGiAaAF3YsRnbiHLsRAitMAKCiLboJkQECM/jpYsY3WPfvUgLXkACgg3ql
OK2XeQOiEeXtT76rV4t2WR4=
=ivrA
-----END PGP SIGNATURE-----
"""


class TagParseTests(ShaFileCheckTests):

    def make_tag_lines(self,
                       object_sha=b"a38d6181ff27824c79fc7df825164a212eff6a3f",
                       object_type_name="commit",
                       name="v2.6.22-rc7",
                       tagger=default_tagger,
                       message=default_message):
        lines = []
        if object_sha is not None:
            lines.append(b"object " + convert3kstr(object_sha, BYTES))
        if object_type_name is not None:
            lines.append(b"type " + convert3kstr(object_type_name, BYTES))
        if name is not None:
            lines.append(b"tag " + convert3kstr(name, BYTES))
        if tagger is not None:
            lines.append(b"tagger " + convert3kstr(tagger, BYTES))
        lines.append(b"")
        if message is not None:
            lines.append(convert3kstr(message, BYTES))
        return lines

    def make_tag_text(self, **kwargs):
        return b"\n".join(self.make_tag_lines(**kwargs))

    def test_parse(self):
        x = Tag()
        x.set_raw_string(self.make_tag_text())
        self.assertEqual(
            "Linus Torvalds <torvalds@woody.linux-foundation.org>", x.tagger)
        self.assertEqual(b"v2.6.22-rc7", x.name)
        object_type, object_sha = x.object
        self.assertEqual(b"a38d6181ff27824c79fc7df825164a212eff6a3f",
                          object_sha)
        self.assertEqual(Commit, object_type)
        self.assertEqual(datetime.datetime.utcfromtimestamp(x.tag_time),
                          datetime.datetime(2007, 7, 1, 19, 54, 34))
        self.assertEqual(-25200, x.tag_timezone)

    def test_parse_no_tagger(self):
        x = Tag()
        x.set_raw_string(self.make_tag_text(tagger=None))
        self.assertEqual(None, x.tagger)
        self.assertEqual(b"v2.6.22-rc7", x.name)

    def test_check(self):
        self.assertCheckSucceeds(Tag, self.make_tag_text())
        self.assertCheckFails(Tag, self.make_tag_text(object_sha=None))
        self.assertCheckFails(Tag, self.make_tag_text(object_type_name=None))
        self.assertCheckFails(Tag, self.make_tag_text(name=None))
        self.assertCheckFails(Tag, self.make_tag_text(name=''))
        self.assertCheckFails(Tag, self.make_tag_text(
          object_type_name="foobar"))
        self.assertCheckFails(Tag, self.make_tag_text(
          tagger="some guy without an email address 1183319674 -0700"))
        self.assertCheckFails(Tag, self.make_tag_text(
          tagger=("Linus Torvalds <torvalds@woody.linux-foundation.org> "
                  "Sun 7 Jul 2007 12:54:34 +0700")))
        self.assertCheckFails(Tag, self.make_tag_text(object_sha="xxx"))

    def test_check_duplicates(self):
        # duplicate each of the header fields
        for i in range(4):
            lines = self.make_tag_lines()
            lines.insert(i, lines[i])
            self.assertCheckFails(Tag, b'\n'.join(lines))

    def test_check_order(self):
        lines = self.make_tag_lines()
        headers = lines[:4]
        rest = lines[4:]
        # of all possible permutations, ensure only the original succeeds
        for perm in permutations(headers):
            perm = list(perm)
            text = b'\n'.join(perm + rest)
            if perm == headers:
                self.assertCheckSucceeds(Tag, text)
            else:
                self.assertCheckFails(Tag, text)


class CheckTests(TestCase):

    def test_check_hexsha(self):
        check_hexsha(a_sha, "failed to check good sha")
        self.assertRaises(ObjectFormatException, check_hexsha, '1' * 39,
                          'sha too short')
        self.assertRaises(ObjectFormatException, check_hexsha, '1' * 41,
                          'sha too long')
        self.assertRaises((ObjectFormatException, binascii.Error), check_hexsha, 'x' * 40,
                          'invalid characters')

    def test_check_identity(self):
        check_identity("Dave Borowitz <dborowitz@google.com>",
                       "failed to check good identity")
        check_identity("<dborowitz@google.com>",
                       "failed to check good identity")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz", "no email")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz <dborowitz", "incomplete email")
        self.assertRaises(ObjectFormatException, check_identity,
                          "dborowitz@google.com>", "incomplete email")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz <<dborowitz@google.com>", "typo")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz <dborowitz@google.com>>", "typo")
        self.assertRaises(ObjectFormatException, check_identity,
                          "Dave Borowitz <dborowitz@google.com>xxx",
                          "trailing characters")


class TimezoneTests(TestCase):

    def test_parse_timezone_utc(self):
        self.assertEqual((0, False), parse_timezone("+0000"))

    def test_parse_timezone_utc_negative(self):
        self.assertEqual((0, True), parse_timezone("-0000"))

    def test_generate_timezone_utc(self):
        self.assertEqual("+0000", format_timezone(0))

    def test_generate_timezone_utc_negative(self):
        self.assertEqual("-0000", format_timezone(0, True))

    def test_parse_timezone_cet(self):
        self.assertEqual((60 * 60, False), parse_timezone("+0100"))

    def test_format_timezone_cet(self):
        self.assertEqual("+0100", format_timezone(60 * 60))

    def test_format_timezone_pdt(self):
        self.assertEqual("-0400", format_timezone(-4 * 60 * 60))

    def test_parse_timezone_pdt(self):
        self.assertEqual((-4 * 60 * 60, False), parse_timezone("-0400"))

    def test_format_timezone_pdt_half(self):
        self.assertEqual("-0440",
            format_timezone(int(((-4 * 60) - 40) * 60)))

    def test_parse_timezone_pdt_half(self):
        self.assertEqual((((-4 * 60) - 40) * 60, False),
            parse_timezone("-0440"))
