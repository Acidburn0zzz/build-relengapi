# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import hashlib
import json
import mock
import os
import shutil
import sys
import tempfile
import tooltool
import unittest

from nose.tools import eq_


class DigestTests(unittest.TestCase):

    def setUp(self):
        self.sample_data = open('test_file.ogg')
        self.sample_algo = 'sha1'
        self.sample_digest = 'de3e3bbffd83c328ad7d9537ad2d03f68fc02e52'

    def test_digest_file(self):
        test_digest = tooltool.digest_file(self.sample_data, self.sample_algo)
        # If this assertion fails, verify that test_file.ogg is an ogg file
        # of Linus Torvalds explaining how he pronounces 'Linux'
        self.assertEqual(test_digest, self.sample_digest)


class BaseFileRecordTest(unittest.TestCase):

    def setUp(self):
        self.sample_file = 'test_file.ogg'
        self.sample_algo = 'sha512'
        self.sample_size = os.path.getsize(self.sample_file)
        with open(self.sample_file) as f:
            self.sample_hash = tooltool.digest_file(f, self.sample_algo)
        self.test_record = tooltool.FileRecord(
            filename=self.sample_file,
            size=self.sample_size,
            digest=self.sample_hash,
            algorithm=self.sample_algo
        )
        # using mkstemp to ensure that the filename generated
        # isn't actually on the system.
        (tmpfd, filename) = tempfile.mkstemp()
        os.close(tmpfd)
        os.remove(filename)
        if os.path.exists(filename):
            self.fail('did not remove %s' % filename)
        self.absent_file = filename


class BaseFileRecordListTest(BaseFileRecordTest):

    def setUp(self):
        BaseFileRecordTest.setUp(self)
        self.record_list = []
        for i in range(0, 4):
            record = copy.deepcopy(self.test_record)
            record.algorithm = i
            self.record_list.append(record)


class TestFileRecord(BaseFileRecordTest):

    def test_present(self):
        # this test feels silly, but things are built on this
        # method, so probably best to test it
        self.assertTrue(self.test_record.present())

    def test_absent(self):
        self.test_record.filename = self.absent_file
        self.assertFalse(self.test_record.present())

    def test_valid_size(self):
        self.assertTrue(self.test_record.validate_size())

    def test_invalid_size(self):
        self.test_record.size += 1
        self.assertFalse(self.test_record.validate_size())

    def test_size_of_missing_file(self):
        self.test_record.filename = self.absent_file
        self.assertRaises(
            tooltool.MissingFileException, self.test_record.validate_size)

    def test_valid_digest(self):
        self.assertTrue(self.test_record.validate_digest())

    def test_invalid_digest(self):
        self.test_record.digest = 'NotValidDigest'
        self.assertFalse(self.test_record.validate_digest())

    def test_digest_of_missing_file(self):
        self.test_record.filename = self.absent_file
        self.assertRaises(
            tooltool.MissingFileException, self.test_record.validate_digest)

    def test_overall_valid(self):
        self.assertTrue(self.test_record.validate())

    def test_overall_invalid_size(self):
        self.test_record.size = 3
        self.assertFalse(self.test_record.validate())

    def test_overall_invalid_digest(self):
        self.test_record.digest = 'NotValidDigest'
        self.assertFalse(self.test_record.validate())

    def test_overall_invalid_missing_file(self):
        self.test_record.filename = self.absent_file
        self.assertRaises(
            tooltool.MissingFileException, self.test_record.validate)

    def test_equality(self):
        test_record2 = copy.deepcopy(self.test_record)
        self.assertEqual(self.test_record, test_record2)
        self.assertEqual(self.test_record, self.test_record)

    def test_inequality(self):
        for i in ['filename', 'size', 'algorithm', 'digest']:
            test_record2 = copy.deepcopy(self.test_record)
            test_record2.__dict__[i] = 'wrong!'
            self.assertNotEqual(self.test_record, test_record2)

    def test_repr(self):
        a = eval(repr(self.test_record))
        self.assertEqual(str(a), str(self.test_record))
        self.assertEqual(a, self.test_record)

    def test_create_file_record(self):
        fr = tooltool.create_file_record(self.sample_file, self.sample_algo)
        self.assertEqual(self.test_record, fr)

    def test_describe_absent(self):
        self.test_record.filename = self.absent_file
        self.assertEqual("'%s' is absent" %
                         self.absent_file, self.test_record.describe())

    def test_describe_present_valid(self):
        self.assertEqual("'%s' is present and valid" % self.test_record.filename,
                         self.test_record.describe())

    def test_describe_present_invalid(self):
        self.test_record.size = 4
        self.test_record.digest = 'NotValidDigest'
        self.assertEqual("'%s' is present and invalid" % self.test_record.filename,
                         self.test_record.describe())


class TestFileRecordJSONCodecs(BaseFileRecordListTest):

    def test_default(self):
        encoder = tooltool.FileRecordJSONEncoder()
        dict_from_encoder = encoder.default(self.test_record)
        for i in ['filename', 'size', 'algorithm', 'digest']:
            self.assertEqual(
                dict_from_encoder[i], self.test_record.__dict__[i])

    def test_default_list(self):
        encoder = tooltool.FileRecordJSONEncoder()
        new_list = encoder.default(self.record_list)
        for record in range(0, len(self.record_list)):
            self.assertEqual(new_list[record],
                             encoder.default(self.record_list[record]))

    def test_unrelated_class(self):
        encoder = tooltool.FileRecordJSONEncoder()

        class Junk:
            pass
        self.assertRaises(
            tooltool.FileRecordJSONEncoderException,
            encoder.default,
            Junk()
        )

    def test_list_with_unrelated_class(self):
        encoder = tooltool.FileRecordJSONEncoder()

        class Junk:
            pass
        self.assertRaises(
            tooltool.FileRecordJSONEncoderException,
            encoder.default,
            [self.test_record, Junk(), self.test_record],
        )

    def test_decode(self):
        json_string = json.dumps(
            self.test_record, cls=tooltool.FileRecordJSONEncoder)
        decoder = tooltool.FileRecordJSONDecoder()
        f = decoder.decode(json_string)
        for i in ['filename', 'size', 'algorithm', 'digest']:
            self.assertEqual(getattr(f, i), self.test_record.__dict__[i])

    def test_json_dumps(self):
        json_string = json.dumps(
            self.test_record, cls=tooltool.FileRecordJSONEncoder)
        dict_from_json = json.loads(json_string)
        for i in ['filename', 'size', 'algorithm', 'digest']:
            self.assertEqual(dict_from_json[i], self.test_record.__dict__[i])

    def test_decode_list(self):
        json_string = json.dumps(
            self.record_list, cls=tooltool.FileRecordJSONEncoder)
        new_list = json.loads(json_string, cls=tooltool.FileRecordJSONDecoder)
        self.assertEquals(len(new_list), len(self.record_list))
        for record in range(0, len(self.record_list)):
            self.assertEqual(new_list[record], self.record_list[record])


class TestManifest(BaseFileRecordTest):

    def setUp(self):
        BaseFileRecordTest.setUp(self)
        self.other_sample_file = 'other-%s' % self.sample_file
        if os.path.exists(self.other_sample_file):
            os.remove(self.other_sample_file)
        shutil.copyfile(self.sample_file, self.other_sample_file)
        self.other_test_record = copy.deepcopy(self.test_record)
        self.other_test_record.filename = self.other_sample_file
        self.test_manifest = tooltool.Manifest(
            [self.test_record, self.other_test_record])

    def tearDown(self):
        try:
            os.remove(self.other_sample_file)
        except OSError:
            pass

    def test_present(self):
        self.assertTrue(self.test_manifest.present())

    def test_absent(self):
        os.remove(self.other_sample_file)
        self.assertFalse(self.test_manifest.present())

    def test_validate_sizes(self):
        self.assertTrue(self.test_manifest.validate_sizes())

    def test_incorrect_size(self):
        self.test_manifest.file_records[1].size = 1
        self.assertFalse(self.test_manifest.validate_sizes())

    def test_validate_digest(self):
        self.assertTrue(self.test_manifest.validate_digests())

    def test_incorrect_digest(self):
        self.test_manifest.file_records[1].digest = 'wrong'
        self.assertFalse(self.test_manifest.validate_digests())

    def test_equality_same_object(self):
        self.assertEqual(self.test_manifest, self.test_manifest)

    def test_equality_deepcopy(self):
        a_deepcopy = copy.deepcopy(self.test_manifest)
        self.assertEqual(self.test_manifest, a_deepcopy)

    def test_equality_copy_method(self):
        a_copy = self.test_manifest.copy()
        self.assertEqual(self.test_manifest, a_copy)

    def test_equality_unrelated(self):
        one = tooltool.Manifest([self.test_record, self.other_test_record])
        two = tooltool.Manifest([self.test_record, self.other_test_record])
        self.assertEqual(one, two)

    def test_json_dump(self):
        tmp_manifest = tempfile.TemporaryFile()
        self.test_manifest.dump(tmp_manifest, fmt='json')
        tmp_manifest.seek(0)
        new_manifest = tooltool.Manifest()
        new_manifest.load(tmp_manifest, fmt='json')
        self.assertEqual(new_manifest, self.test_manifest)

    def test_json_dumps(self):
        s = self.test_manifest.dumps(fmt='json')
        new_manifest = tooltool.Manifest()
        new_manifest.loads(s, fmt='json')
        self.assertEqual(new_manifest, self.test_manifest)

    def test_load_empty_json_file(self):
        empty = tempfile.TemporaryFile()
        manifest = tooltool.Manifest()
        self.assertRaises(tooltool.InvalidManifest,
                          manifest.load, empty, fmt='json')

    def test_load_empty_json_string(self):
        empty = ''
        manifest = tooltool.Manifest()
        self.assertRaises(tooltool.InvalidManifest,
                          manifest.loads, empty, fmt='json')


class TestManifestOperations(BaseFileRecordTest):

    def setUp(self):
        BaseFileRecordTest.setUp(self)
        self.sample_manifest = tooltool.Manifest([self.test_record])
        self.sample_manifest_file = '.testmanifest'
        self.test_dir = 'test-dir'
        self.startingwd = os.getcwd()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.mkdir(self.test_dir)
        with open(os.path.join(self.test_dir, self.sample_manifest_file), 'w') as tmpfile:
            self.sample_manifest.dump(tmpfile, fmt='json')

    def tearDown(self):
        os.chdir(self.startingwd)
        shutil.rmtree(self.test_dir)


def call_main(*args):
    try:
        old_stderr = sys.stderr
        sys.stderr = sys.stdout
        try:
            return tooltool.main(list(args), _skip_logging=True)
        except SystemExit, e:
            return "exit {}".format(e.code)
    finally:
        sys.stderr = old_stderr


def test_main_help():
    eq_(call_main('tooltool', '--help'), "exit 0")


def test_main_no_command():
    eq_(call_main('tooltool'), "exit 2")


def test_main_bad_command():
    eq_(call_main('tooltool', 'foo'), 1)


def test_main_bad_algorithm():
    eq_(call_main('tooltool', '--algorithm', 'sha13', 'fetch'), 'exit 2')


def test_command_list():
    with mock.patch('tooltool.list_manifest') as list_manifest:
        eq_(call_main('tooltool', 'list', '--manifest', 'foo.tt'), 0)
        list_manifest.assert_called_with('foo.tt')


def test_command_validate():
    with mock.patch('tooltool.validate_manifest') as validate_manifest:
        eq_(call_main('tooltool', 'validate'), 0)
        validate_manifest.assert_called_with('manifest.tt')


def test_command_add():
    with mock.patch('tooltool.add_files') as add_files:
        eq_(call_main('tooltool', 'add', 'a', 'b'), 0)
        add_files.assert_called_with('manifest.tt', 'sha512', ['a', 'b'])


def test_command_purge_no_folder():
    with mock.patch('tooltool.purge') as purge:
        eq_(call_main('tooltool', 'purge'), 1)
        assert not purge.called


def test_command_purge():
    with mock.patch('tooltool.purge') as purge:
        eq_(call_main('tooltool', 'purge', '--cache', 'foo'), 1)
        purge.assert_called_with(folder='foo', gigs=0)


def test_command_purge_size():
    with mock.patch('tooltool.purge') as purge:
        eq_(call_main('tooltool', 'purge', '--size', '10', '--cache', 'foo'), 1)
        purge.assert_called_with(folder='foo', gigs=10)


def test_command_fetch_no_url():
    with mock.patch('tooltool.fetch_files') as fetch_files:
        eq_(call_main('tooltool', 'fetch'), 1)
        assert not fetch_files.called


def test_command_fetch():
    with mock.patch('tooltool.fetch_files') as fetch_files:
        eq_(call_main('tooltool', 'fetch', 'a', 'b', '--url', 'http://foo'), 0)
        fetch_files.assert_called_with('manifest.tt', ['http://foo'], ['a', 'b'],
                                       cache_folder=None, auth_file=None)


def test_command_package():
    with mock.patch('tooltool.fetch_files') as fetch_files:
        eq_(call_main('tooltool', 'fetch', 'a', 'b', '--url', 'http://foo'), 0)
        fetch_files.assert_called_with('manifest.tt', ['http://foo'], ['a', 'b'],
                                       cache_folder=None, auth_file=None)


class PurgeTests(unittest.TestCase):

    def setUp(self):
        self.test_dir = 'test-dir'
        self.startingwd = os.getcwd()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.mkdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.startingwd)
        shutil.rmtree(self.test_dir)

    def fake_freespace(self, p):
        # A fake 10G drive, with each file = 1G
        eq_(p, self.test_dir)
        return 1024 ** 3 * (10 - len(os.listdir(self.test_dir)))

    def add_files(self, *files):
        now = 1426127031
        # add files, with ordered mtime
        for f in files:
            path = os.path.join(self.test_dir, f)
            open(path, "w")
            os.utime(path, (now, now))
            now += 10

    def test_purge_fails(self):
        path = os.path.join(self.test_dir, 'sticky')
        open(path, 'w')
        os.chmod(self.test_dir, 0o500)  # prevent delete
        try:
            tooltool.purge(self.test_dir, 0)
            eq_(os.listdir(self.test_dir), ['sticky'])
        finally:
            os.chmod(self.test_dir, 0o700)

    def test_purge_nonfile_not_deleted(self):
        path = os.path.join(self.test_dir, 'somedir')
        os.mkdir(path)
        tooltool.purge(self.test_dir, 0)
        eq_(os.listdir(self.test_dir), ['somedir'])

    def test_purge_nonzero(self):
        # six files means six gigs consumed, so we'll delete two
        self.add_files("one", "two", "three", "four", "five", "six")
        with mock.patch('tooltool.freespace') as freespace:
            freespace.side_effect = self.fake_freespace
            tooltool.purge(self.test_dir, 6)
        eq_(sorted(os.listdir(self.test_dir)),
            sorted(['three', 'four', 'five', 'six']))

    def test_purge_no_need(self):
        self.add_files("one", "two")
        with mock.patch('tooltool.freespace') as freespace:
            freespace.side_effect = self.fake_freespace
            tooltool.purge(self.test_dir, 4)
        eq_(sorted(os.listdir(self.test_dir)),
            sorted(['one', 'two']))

    def test_purge_zero(self):
        self.add_files("one", "two", "three")
        tooltool.purge(self.test_dir, 0)
        eq_(os.listdir(self.test_dir), [])

    def test_freespace(self):
        # we can't set up a dedicated partition for this test, so just assume
        # the disk isn't full (other tests assume this too, really)
        assert tooltool.freespace(self.test_dir) > 0


class FetchTests(unittest.TestCase):

    _server_files = ['one', 'two', 'three']
    server_files_by_hash = {hashlib.sha512(v).hexdigest(): v
                            for v in _server_files}
    server_corrupt = False
    urls = ['http://a', 'http://2']

    def setUp(self):
        self.test_dir = os.path.abspath('test-dir')
        self.startingwd = os.getcwd()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.mkdir(self.test_dir)
        self.cache_dir = os.path.join(self.test_dir, 'cache')
        # fetch expects to work in the cwd
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.startingwd)
        shutil.rmtree(self.test_dir)

    def fake_fetch_file(self, urls, file_record, auth_file=None):
        eq_(urls, self.urls)
        if file_record.digest in self.server_files_by_hash:
            if self.server_corrupt:
                content = 'XXX'
            else:
                content = self.server_files_by_hash[file_record.digest]
            fd, temp_path = tempfile.mkstemp(dir=self.test_dir)
            os.write(fd, content)
            os.close(fd)
            return os.path.split(temp_path)[1]
        else:
            return None

    def add_file_to_dir(self, file, corrupt=False):
        content = 'X' * len(file) if corrupt else file
        open(os.path.join(self.test_dir, "file-{}".format(file)), "w").write(content)

    def add_file_to_cache(self, file, corrupt=False):
        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir)
        digest = hashlib.sha512(file).hexdigest()
        content = 'X' * len(file) if corrupt else file
        open(os.path.join(self.cache_dir, digest), "w").write(content)

    def make_manifest(self, filename, *files, **kwargs):
        unpack = kwargs.pop('unpack', False)
        manifest = []
        for file in files:
            manifest.append({
                'filename': 'file-{}'.format(file),
                'size': len(file),
                'algorithm': 'sha512',
                'digest': hashlib.sha512(file).hexdigest(),
                'unpack': unpack,
            })
        json.dump(manifest, open(filename, "w"))

    def assert_files(self, *files):
        eq_(sorted([f for f in os.listdir(self.test_dir)
                    if f != 'cache' and not f.endswith('.tt')]),
            sorted(['file-' + f for f in files]))
        for f in files:
            eq_(open('file-' + f).read(), f)

    def assert_cached_files(self, *files):
        if not files and not os.path.exists(self.cache_dir):
            return
        hashes = [hashlib.sha512(f).hexdigest() for f in files]
        eq_(sorted(os.listdir(self.cache_dir)), sorted(hashes))
        for f, h in zip(files, hashes):
            eq_(open(os.path.join(self.cache_dir, h)).read(), f)

    # tests

    def test_no_manifest(self):
        """If the given manifest isn't present, fetch_files fails"""
        eq_(tooltool.fetch_files('not-present.tt', self.urls), False)

    def test_all_present(self):
        """When all expected files are present, fetch_files does not fetch anything"""
        self.add_file_to_dir('one')
        self.add_file_to_dir('two')
        self.make_manifest('manifest.tt', 'one', 'two')
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = RuntimeError
            eq_(tooltool.fetch_files('manifest.tt', self.urls, cache_folder='cache'),
                True)
        self.assert_files('one', 'two')
        self.assert_cached_files()

    def test_all_cached(self):
        """When all expected files are in the cache, fetch_files copies but
        does not fetch"""
        self.add_file_to_cache('one')
        self.add_file_to_cache('two')
        self.make_manifest('manifest.tt', 'one', 'two')
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = RuntimeError
            eq_(tooltool.fetch_files('manifest.tt', self.urls, cache_folder='cache'),
                True)
        self.assert_files('one', 'two')
        self.assert_cached_files('one', 'two')

    def test_all_missing(self):
        """When all expected files are not found, they are fetched."""
        self.make_manifest('manifest.tt', 'one', 'two')
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = self.fake_fetch_file
            eq_(tooltool.fetch_files('manifest.tt', self.urls, cache_folder='cache'),
                True)
        self.assert_files('one', 'two')
        self.assert_cached_files('one', 'two')

    def test_missing_not_on_server(self):
        """When the file is missing everywhere including the server, fetch fails"""
        self.make_manifest('manifest.tt', 'ninetynine')
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = self.fake_fetch_file
            eq_(tooltool.fetch_files('manifest.tt', self.urls, cache_folder='cache'),
                False)
        self.assert_files()
        self.assert_cached_files()

    def test_missing_corrupt_on_server(self):
        """When the file is missing everywhere and coorrupt the server, fetch fails"""
        self.make_manifest('manifest.tt', 'one')
        with mock.patch('tooltool.fetch_file') as fetch_file:
            self.server_corrupt = True
            fetch_file.side_effect = self.fake_fetch_file
            eq_(tooltool.fetch_files('manifest.tt', self.urls, cache_folder='cache'),
                False)
        self.assert_files()
        self.assert_cached_files()

    def test_local_corrupt_but_cached(self):
        """When the local files are corrupt but the cache is OK, the cache is used"""
        self.add_file_to_dir('one', corrupt=True)
        self.add_file_to_cache('one')
        self.make_manifest('manifest.tt', 'one')
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = RuntimeError
            eq_(tooltool.fetch_files('manifest.tt', self.urls, cache_folder='cache'),
                True)
        self.assert_files('one')
        self.assert_cached_files('one')

    def test_local_missing_cache_corrupt(self):
        """When the local files are missing  and the cache is corrupt, fetch"""
        self.add_file_to_cache('one', corrupt=True)
        self.make_manifest('manifest.tt', 'one')
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = self.fake_fetch_file
            eq_(tooltool.fetch_files('manifest.tt', self.urls, cache_folder='cache'),
                True)
        self.assert_files('one')
        self.assert_cached_files('one')

    def test_missing_unwritable_cache(self):
        """If fetch downloads files but can't write to the cache, it still succeeds"""
        self.make_manifest('manifest.tt', 'one')
        os.mkdir(self.cache_dir, 0o500)
        try:
            with mock.patch('tooltool.fetch_file') as fetch_file:
                fetch_file.side_effect = self.fake_fetch_file
                eq_(tooltool.fetch_files('manifest.tt', self.urls, cache_folder='cache'),
                    True)
            self.assert_files('one')
            self.assert_cached_files()
        finally:
            os.chmod(self.cache_dir, 0o700)

    def test_mixed(self):
        """fetch creates a dir containing the right files given a mix of file states"""
        self.add_file_to_dir('one', corrupt=True)
        self.add_file_to_cache('two', corrupt=True)
        self.add_file_to_dir('four')
        self.add_file_to_cache('five')
        self.make_manifest('manifest.tt', 'one', 'two', 'three', 'four', 'five')
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = self.fake_fetch_file
            eq_(tooltool.fetch_files('manifest.tt', self.urls, cache_folder='cache'),
                True)
        self.assert_files('one', 'two', 'three', 'four', 'five')
        self.assert_cached_files('one', 'two', 'three', 'five')

    def test_file_list(self):
        """fetch only fetches the files requested in the file list"""
        self.add_file_to_dir('one')
        self.add_file_to_cache('five')
        self.make_manifest('manifest.tt', 'one', 'five', 'nine')
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = self.fake_fetch_file
            eq_(tooltool.fetch_files('manifest.tt', self.urls,
                                     cache_folder='cache',
                                     filenames=['five']),
                True)
        self.assert_files('one', 'five')
        self.assert_cached_files('five')

    def test_unpack(self):
        """When asked to unpack files, fetch calls untar_file."""
        self.add_file_to_dir('four')
        self.add_file_to_cache('five')
        self.make_manifest('manifest.tt', 'three', 'four', 'five', unpack=True)
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = self.fake_fetch_file
            with mock.patch('tooltool.untar_file') as untar_file:
                eq_(tooltool.fetch_files('manifest.tt', self.urls,
                                         cache_folder='cache'),
                    True)
                untar_file.assert_has_calls([
                    mock.call('file-three'),
                    mock.call('file-four'),
                    mock.call('file-five'),
                ], any_order=True)
        self.assert_files('three', 'four', 'five')
        self.assert_cached_files('three', 'five')

    def test_unpack_fails(self):
        """When asked to unpack files, and the unpack fails, fetch fails."""
        self.make_manifest('manifest.tt', 'one', unpack=True)
        with mock.patch('tooltool.fetch_file') as fetch_file:
            fetch_file.side_effect = self.fake_fetch_file
            with mock.patch('tooltool.untar_file') as untar_file:
                untar_file.side_effect = lambda f: False
                eq_(tooltool.fetch_files('manifest.tt', self.urls,
                                         cache_folder='cache'),
                    False)
                untar_file.assert_called_with('file-one')
        self.assert_files('one')
