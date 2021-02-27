#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys
import shutil
from nose.tools import *

# for debugging only
from os import listdir
from os.path import isfile, join

from ext.mediafile import MediaFile

import logging

logging.basicConfig(level=10)
logger = logging.getLogger(__name__)

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parentdir)

logger.debug("parentdir: %s" % parentdir)

from _common_test import TestDummyResponse, DummyDiscogsAlbum

from discogstagger.tagger_config import TaggerConfig
from discogstagger.discogsalbum import DiscogsConnector
from discogstagger.taggerutils import TaggerUtils, TagHandler, FileHandler, TaggerError

class TaggerUtilsBase(object):

    def setUp(self):
        self.ogsrelid = "1448190"

        # construct config with only default values
        self.tagger_config = TaggerConfig(os.path.join(parentdir, "test/empty.conf"))

        dummy_response = TestDummyResponse(self.ogsrelid)
        discogs_album = DummyDiscogsAlbum(dummy_response)
        self.album = discogs_album.map()

    def tearDown(self):
        self.ogsrelid = None
        self.tagger_config = None
        self.album = None

class TestTaggerUtils(TaggerUtilsBase):

    def test_value_from_tag_format(self):
        taggerutils = TaggerUtils("dummy_source_dir", "dummy_dest_dir", self.tagger_config, self.album)

        format = taggerutils._value_from_tag_format("%DISCNO%", 1, 1, ".mp3")
        assert format == "1"

        format = taggerutils._value_from_tag_format("%ALBARTIST%-%ALBTITLE%")
        assert format == "Various-Megahits 2001 Die Erste"

        format = taggerutils._value_from_tag_format("%ALBARTIST%-%ALBTITLE%-(%CATNO%)-%YEAR%")
        assert format == "Various-Megahits 2001 Die Erste-(560 938-2)-2001"

        format = taggerutils._value_from_tag_format("%TRACKNO%-%ARTIST%-%TITLE%%TYPE%")
        assert format == "01-Gigi D'Agostino-La Passion (Radio Cut).mp3"

        format = taggerutils._value_from_tag_format("%TRACKNO%-%ARTIST%-%TITLE%", 1, 1, ".flac")
        assert format == "01-Gigi D'Agostino-La Passion (Radio Cut)"

    def test_value_from_tag(self):
        taggerutils = TaggerUtils("dummy_source_dir", "dummy_dest_dir", self.tagger_config, self.album)

        format = taggerutils._value_from_tag("%ALBARTIST%-%ALBTITLE%")
        assert format == "various-megahits_2001_die_erste"

        format = taggerutils._value_from_tag("%ALBARTIST%-%ALBTITLE%-(%CATNO%)-%YEAR%")
        assert format == "various-megahits_2001_die_erste-(560_938-2)-2001"

        format = taggerutils._value_from_tag("%TRACKNO%-%ARTIST%-%TITLE%%TYPE%")
        assert format == "01-gigi_dagostino-la_passion_(radio_cut).mp3"

        format = taggerutils._value_from_tag("%TRACKNO%-%ARTIST%-%TITLE%", 1, 1, ".flac")
        assert format == "01-gigi_dagostino-la_passion_(radio_cut)"

    def test_dest_dir_name(self):
        taggerutils = TaggerUtils("dummy_source_dir", "./dummy_dest_dir", self.tagger_config, self.album)
        assert taggerutils.dest_dir_name == "dummy_dest_dir/various-megahits_2001_die_erste-(560_938-2)-2001"

        taggerutils = TaggerUtils("dummy_source_dir", "dummy_dest_dir", self.tagger_config, self.album)
        assert taggerutils.dest_dir_name == "dummy_dest_dir/various-megahits_2001_die_erste-(560_938-2)-2001"

        taggerutils = TaggerUtils("dummy_source_dir", "/dummy_dest_dir", self.tagger_config, self.album)
        assert taggerutils.dest_dir_name == "/dummy_dest_dir/various-megahits_2001_die_erste-(560_938-2)-2001"

        taggerutils = TaggerUtils("dummy_source_dir", "dummy_dest_dir", self.tagger_config, self.album)
        taggerutils.dir_format = "%GENRE%/%ALBARTIST%/%ALBTITLE%-(%CATNO%)-%YEAR%"
        assert taggerutils.dest_dir_name == "dummy_dest_dir/electronic/various/megahits_2001_die_erste-(560_938-2)-2001"


class TestTaggerUtilFiles(TaggerUtilsBase):

    def setUp(self):
        TaggerUtilsBase.setUp(self)

        self.source_dir = "/tmp/dummy_source_dir"
        self.target_dir = "/tmp/dummy_dest_dir"

        self.source_file = "test/files/test.flac"
        self.source_copy_file = "test/files/test.txt"

        os.mkdir(self.source_dir)
        os.mkdir(self.target_dir)

    def tearDown(self):
        TaggerUtilsBase.tearDown(self)

        # we are removing this directory in one test (see FileHandler)
        # therefor we need to be cautious ;-)
        if os.path.exists(self.source_dir):
            shutil.rmtree(self.source_dir)
        shutil.rmtree(self.target_dir)

    def copy_files(self, album):
        for i, disc in enumerate(album.discs):
            discno = i + 1
            disc = album.disc(discno)

            dir_name = "disc%d" % discno
            self.album.disc(discno).sourcedir = dir_name
            multi_source_dir = os.path.join(self.source_dir, dir_name)
            logger.debug("multi source dir: %s" % multi_source_dir)
            if not os.path.exists(multi_source_dir):
                os.mkdir(multi_source_dir)

            for i, track in enumerate(disc.tracks):
                trackno = i + 1
                target_file_name = "%.2d-song.flac" % trackno
                shutil.copyfile(self.source_file, os.path.join(multi_source_dir, target_file_name))

            target_file_name = "album.m3u"
            logger.debug("copy to %s" % os.path.join(multi_source_dir, target_file_name))
            shutil.copyfile(self.source_copy_file, os.path.join(multi_source_dir, target_file_name))

            target_file_name = "album.cue"
            logger.debug("copy to %s" % os.path.join(multi_source_dir, target_file_name))
            shutil.copyfile(self.source_copy_file, os.path.join(multi_source_dir, target_file_name))

        target_file_name = "id.txt"
        logger.debug("copy to %s" % os.path.join(self.source_dir, target_file_name))
        shutil.copyfile(self.source_copy_file, os.path.join(self.source_dir, target_file_name))

        # use multiple files previous in the list to the used disc name
        target_file_name = "a1.txt"
        logger.debug("copy to %s" % os.path.join(self.source_dir, target_file_name))
        shutil.copyfile(self.source_copy_file, os.path.join(self.source_dir, target_file_name))

        # use multiple files previous in the list to the used disc name
        target_file_name = "a2.txt"
        logger.debug("copy to %s" % os.path.join(self.source_dir, target_file_name))
        shutil.copyfile(self.source_copy_file, os.path.join(self.source_dir, target_file_name))

    def copy_files_single_album(self, track_no):
        # copy file to source directory and rename it
        for i in range(1, track_no + 1):
            target_file_name = "%.2d-song.flac" % i
            shutil.copyfile(self.source_file, os.path.join(self.source_dir, target_file_name))

        target_file_name = "album.m3u"
        shutil.copyfile(self.source_copy_file, os.path.join(self.source_dir, target_file_name))

        target_file_name = "album.cue"
        shutil.copyfile(self.source_copy_file, os.path.join(self.source_dir, target_file_name))

        target_file_name = "id.txt"
        shutil.copyfile(self.source_copy_file, os.path.join(self.source_dir, target_file_name))

    def test_get_target_list_multi_disc(self):
        # copy file to source directory and rename it
        self.copy_files(self.album)

        target_file_name = "id.txt"
        shutil.copyfile(self.source_copy_file, os.path.join(self.source_dir, target_file_name))

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        taggerutils._get_target_list()

        assert self.album.copy_files[0] == "a1.txt"
        assert self.album.copy_files[1] == "a2.txt"
        assert self.album.copy_files[2] == "id.txt"

        assert self.album.sourcedir == self.source_dir
        assert self.album.discs[0].sourcedir == "disc1"
        assert self.album.discs[1].sourcedir == "disc2"

        assert self.album.target_dir == os.path.join(self.target_dir, "various-megahits_2001_die_erste-(560_938-2)-2001")

        assert self.album.discs[0].target_dir == "megahits_2001_die_erste-disc1"
        assert self.album.discs[1].target_dir == "megahits_2001_die_erste-disc2"

        assert self.album.discs[0].copy_files[0] == "album.cue"
        assert self.album.discs[0].copy_files[1] == "album.m3u"

        assert self.album.discs[1].copy_files[0] == "album.cue"
        assert self.album.discs[1].copy_files[1] == "album.m3u"

        assert self.album.discs[0].tracks[0].orig_file == "01-song.flac"
        assert self.album.discs[0].tracks[0].new_file == "01-gigi_dagostino-la_passion_(radio_cut).flac"

        assert self.album.discs[0].tracks[19].orig_file == "20-song.flac"
        assert self.album.discs[0].tracks[19].new_file == "20-papa_roach-last_resort_(album_version_explizit).flac"

        assert self.album.discs[1].tracks[0].orig_file == "01-song.flac"
        assert self.album.discs[1].tracks[0].new_file == "01-die_3_generation-ich_will_dass_du_mich_liebst_(radio_edit).flac"

        assert self.album.discs[1].tracks[19].orig_file == "20-song.flac"
        assert self.album.discs[1].tracks[19].new_file == "20-jay-z-i_just_wanna_love_u_(give_it_2_me)_(radio_edit).flac"

    def test_get_target_list_single_disc(self):
        self.ogsrelid = "3083"

        # construct config with only default values
        tagger_config = TaggerConfig(os.path.join(parentdir, "test/empty.conf"))

        dummy_response = TestDummyResponse(self.ogsrelid)
        discogs_album = DummyDiscogsAlbum(dummy_response)
        self.album = discogs_album.map()

        # copy file to source directory and rename it
        self.copy_files_single_album(17)

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        taggerutils._get_target_list()

        assert self.album.sourcedir == self.source_dir
        assert self.album.discs[0].sourcedir == None

        assert self.album.target_dir == os.path.join(self.target_dir, "yonderboi-shallow_and_profound-(molecd023-2)-2000")
        assert self.album.discs[0].target_dir == None

        assert self.album.discs[0].tracks[0].orig_file == "01-song.flac"
        assert self.album.discs[0].tracks[0].new_file == "01-yonderboi-intro.flac"

        assert self.album.discs[0].tracks[16].orig_file == "17-song.flac"
        assert self.album.discs[0].tracks[16].new_file == "17-yonderboi-outro.flac"

        assert self.album.discs[0].copy_files[0] == "album.cue"
        assert self.album.discs[0].copy_files[1] == "album.m3u"
        assert self.album.discs[0].copy_files[2] == "id.txt"

    def test_get_target_list_single_disc_with_subtracks(self):
        """
            Some releases do have "subtracks" (see 513904, track 15), which means that there
            are two tracks assigned to one position (e.g. 15.1 and 15.2). This gets quite
            complicated, because this is rather similar to the multi-disc handling
        """
        self.ogsrelid = "513904"

        # construct config with only default values
        tagger_config = TaggerConfig(os.path.join(parentdir, "test/empty.conf"))

        dummy_response = TestDummyResponse(self.ogsrelid)
        discogs_album = DummyDiscogsAlbum(dummy_response)
        self.album = discogs_album.map()

        # copy file to source directory and rename it
        self.copy_files_single_album(14)

        target_file_name = "513904.json"
        shutil.copyfile(self.source_copy_file, os.path.join(self.source_dir, target_file_name))

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        try:
            taggerutils._get_target_list()
        except TaggerError as te:
            assert True
            return

        assert False

    def test_get_target_list_with_multiple_release_artists(self):
        """
            Some releases do have multiple release-artists (see 2452735),
            the release artists are treated differently from the track artists,
            check it in here, to make sure it is really working (should be in
            test_discogs.py usually)
        """
        self.ogsrelid = "2454735"

        # construct config with only default values
        tagger_config = TaggerConfig(os.path.join(parentdir, "test/empty.conf"))

        dummy_response = TestDummyResponse(self.ogsrelid)
        discogs_album = DummyDiscogsAlbum(dummy_response)
        self.album = discogs_album.map()

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        taggerutils._get_target_list()

        assert len(self.album.artists) == 2
        assert self.album.artists[0] == "Frank Zappa"
        assert self.album.artists[1] == "Ensemble Modern"

        assert self.album.artist == "Frank Zappa"
        assert self.album.discs[0].tracks[0].new_file == "01-frank_zappa-intro"

    def test_create_file_from_template(self):
        self.ogsrelid = "3083"

        # construct config with only default values
        tagger_config = TaggerConfig(os.path.join(parentdir, "test/empty.conf"))

        dummy_response = TestDummyResponse(self.ogsrelid)
        discogs_album = DummyDiscogsAlbum(dummy_response)
        self.album = discogs_album.map()

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        create_file = os.path.join(self.target_dir, "info.nfo")
        assert taggerutils.create_file_from_template("/info.txt", create_file)

        assert os.path.exists(create_file)

        assert taggerutils.create_nfo(self.target_dir)

        # copy file to source directory and rename it
        self.copy_files_single_album(17)

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        taggerutils._get_target_list()
        assert self.album.discs[0].tracks[0].new_file == "01-yonderboi-intro.flac"
        assert taggerutils.create_m3u(self.target_dir)

class TestFileHandler(TestTaggerUtilFiles):

    def setUp(self):
        TestTaggerUtilFiles.setUp(self)
        self.target_file_name = "test.flac"

    def tearDown(self):
        TestTaggerUtilFiles.tearDown(self)
        self.tagger_config = None

    def test_remove_source_dir(self):
        self.album.sourcedir = self.source_dir

        assert self.tagger_config.getboolean("details", "keep_original")

        testFileHandler = FileHandler(self.album, self.tagger_config)

        target_file = os.path.join(self.album.sourcedir, "id.txt")
        shutil.copyfile(self.source_copy_file, target_file)

        assert os.path.exists(target_file)

        testFileHandler.remove_source_dir()

        assert os.path.exists(self.album.sourcedir)
        assert os.path.exists(target_file)

        # construct config with only default values
        self.tagger_config = TaggerConfig(os.path.join(parentdir, "test/test_values.conf"))

        assert not self.tagger_config.getboolean("details", "keep_original")

        testFileHandler = FileHandler(self.album, self.tagger_config)

        assert os.path.exists(target_file)

        testFileHandler.remove_source_dir()

        assert not os.path.exists(self.album.sourcedir)
        assert not os.path.exists(target_file)

    def test_copy_files(self):
        testTagUtils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        testFileHandler = FileHandler(self.album, self.tagger_config)

        self.copy_files(self.album)

        testTagUtils._get_target_list()

        testFileHandler.copy_files()

        assert os.path.exists(self.album.sourcedir)
        assert os.path.exists(self.album.target_dir)

        disc_dir = os.path.join(self.album.target_dir, self.album.disc(1).target_dir)
        assert os.path.exists(disc_dir)

        disc_dir = os.path.join(self.album.target_dir, self.album.disc(2).target_dir)
        assert os.path.exists(disc_dir)

        track_file = os.path.join(self.album.target_dir,
            self.album.disc(1).target_dir, self.album.disc(1).track(1).new_file)
        assert os.path.exists(track_file)

        track_file = os.path.join(self.album.target_dir,
            self.album.disc(1).target_dir, self.album.disc(1).track(20).new_file)
        assert os.path.exists(track_file)

        track_file = os.path.join(self.album.target_dir,
            self.album.disc(2).target_dir, self.album.disc(2).track(1).new_file)
        assert os.path.exists(track_file)

        track_file = os.path.join(self.album.target_dir,
            self.album.disc(2).target_dir, self.album.disc(2).track(20).new_file)
        assert os.path.exists(track_file)

    def test_embed_coverart_track(self):
        testTagUtils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        testFileHandler = FileHandler(self.album, self.tagger_config)

        self.copy_files(self.album)

        testTagUtils._get_target_list()

        testFileHandler.copy_files()

        assert os.path.exists(self.album.sourcedir)
        assert os.path.exists(self.album.target_dir)

        track = self.album.disc(1).track(1)
        track_file = os.path.join(self.album.target_dir,
            self.album.disc(1).target_dir, track.new_file)

        source_file = "test/files/cover.jpeg"
        target_dir = os.path.join(self.album.target_dir, self.album.disc(1).target_dir)
        image_file = os.path.join(target_dir, "cover.jpeg")
        shutil.copyfile(source_file, image_file)
        imgdata = open(image_file).read()

        testFileHandler.embed_coverart_track(self.album.disc(1), track, imgdata)

        assert os.path.exists(track_file)

        metadata = MediaFile(track_file)

        assert not metadata.art == None

        track = self.album.disc(1).track(2)
        track_file = os.path.join(self.album.target_dir,
            self.album.disc(1).target_dir, track.new_file)
        metadata = MediaFile(track_file)

        assert metadata.art == None

    def test_embed_coverart_album(self):
        testTagUtils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        testFileHandler = FileHandler(self.album, self.tagger_config)

        self.copy_files(self.album)

        testTagUtils._get_target_list()

        testFileHandler.copy_files()

        assert os.path.exists(self.album.sourcedir)
        assert os.path.exists(self.album.target_dir)

        source_file = "test/files/cover.jpeg"
        image_file = os.path.join(self.album.target_dir, "folder.jpg")
        shutil.copyfile(source_file, image_file)

        testFileHandler.embed_coverart_album()

        track = self.album.disc(1).track(1)
        track_file = os.path.join(self.album.target_dir,
            self.album.disc(1).target_dir, track.new_file)
        metadata = MediaFile(track_file)

        assert not metadata.art == None

    def test_copy_other_files(self):
        assert not self.tagger_config.getboolean("details", "copy_other_files")

        testTagUtils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        self.copy_files(self.album)

        testTagUtils._get_target_list()

        testFileHandler = FileHandler(self.album, self.tagger_config)

        testFileHandler.copy_other_files()

        album_target_dir = self.album.target_dir
        assert not os.path.exists(os.path.join(album_target_dir, "id.txt"))

        disc_target_dir = os.path.join(album_target_dir, self.album.disc(1).target_dir)
        assert not os.path.exists(os.path.join(disc_target_dir, "album.cue"))

        disc_target_dir = os.path.join(album_target_dir, self.album.disc(2).target_dir)
        assert not os.path.exists(os.path.join(disc_target_dir, "album.cue"))

        # construct config with only default values
        self.tagger_config = TaggerConfig(os.path.join(parentdir, "test/test_values.conf"))

        assert self.tagger_config.getboolean("details", "copy_other_files")

        testTagUtils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        testFileHandler = FileHandler(self.album, self.tagger_config)

        self.copy_files(self.album)

        testFileHandler.copy_other_files()

        album_target_dir = self.album.target_dir
        logger.debug("album_target_dir: %s" % album_target_dir)
        assert os.path.exists(os.path.join(album_target_dir, "id.txt"))

        disc_target_dir = os.path.join(album_target_dir, self.album.disc(1).target_dir)
        assert os.path.exists(os.path.join(disc_target_dir, "album.cue"))

        disc_target_dir = os.path.join(album_target_dir, self.album.disc(2).target_dir)
        assert os.path.exists(os.path.join(disc_target_dir, "album.cue"))

    def test_create_done_file(self):
        testTagUtils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        self.copy_files(self.album)

        testFileHandler = FileHandler(self.album, self.tagger_config)

        assert not os.path.exists(os.path.join(self.album.sourcedir, "dt.done"))

        testFileHandler.create_done_file()

        assert os.path.exists(os.path.join(self.album.sourcedir, "dt.done"))

    def test_get_images(self):
        """ It downloads only one image, since this is the default configuration
            This test needs network connection, as well as authentication support
        """
        testTagUtils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        self.copy_files(self.album)

        testTagUtils._get_target_list()

        # the following stuff is only needed in the test, since we cannot use
        # a config option for these values ;-(
        # we are unfortunately treated to login every time this method is called ;-(

        consumer_key = None
        consumer_secret = None

        if os.environ.has_key("TRAVIS_DISCOGS_CONSUMER_KEY"):
            consumer_key = os.environ.get('TRAVIS_DISCOGS_CONSUMER_KEY')
        if os.environ.has_key("TRAVIS_DISCOGS_CONSUMER_SECRET"):
            consumer_secret = os.environ.get("TRAVIS_DISCOGS_CONSUMER_SECRET")

        config = self.tagger_config
        config.set("discogs", "consumer_key", consumer_key)
        config.set("discogs", "consumer_secret", consumer_secret)

        discogs_connection = DiscogsConnector(config)
        testFileHandler = FileHandler(self.album, config)
        testFileHandler.get_images(discogs_connection)

        onlyfiles = [ f for f in listdir(self.album.target_dir) if isfile(join(self.album.target_dir, f))]
        logger.debug("files: %s " % onlyfiles)

        assert os.path.exists(os.path.join(self.album.target_dir, "folder.jpg"))
        assert not os.path.exists(os.path.join(self.album.target_dir, "image-01.jpg"))

    def test_get_images_wo_folderjpg(self):
        """ Downloads several images from discogs, using authentication
            This test needs network connection, as well as authentication support
        """
        # construct config with only default values
        config = TaggerConfig(os.path.join(parentdir, "test/test_values.conf"))

        testTagUtils = TaggerUtils(self.source_dir, self.target_dir, config, self.album)

        self.copy_files(self.album)

        testTagUtils._get_target_list()

        # the following stuff is only needed in the test, since we cannot use
        # a config option for these values ;-(
        # we are unfortunately treated to login every time this method is called ;-(

        if os.environ.has_key("TRAVIS_DISCOGS_CONSUMER_KEY"):
            consumer_key = os.environ.get('TRAVIS_DISCOGS_CONSUMER_KEY')
        if os.environ.has_key("TRAVIS_DISCOGS_CONSUMER_SECRET"):
            consumer_secret = os.environ.get("TRAVIS_DISCOGS_CONSUMER_SECRET")

        config.set("discogs", "consumer_key", consumer_key)
        config.set("discogs", "consumer_secret", consumer_secret)

        discogs_connection = DiscogsConnector(config)
        testFileHandler = FileHandler(self.album, config)
        testFileHandler.get_images(discogs_connection)

        onlyfiles = [ f for f in listdir(self.album.target_dir) if isfile(join(self.album.target_dir, f))]
        logger.debug("files: %s " % onlyfiles)

        logger.debug('checking %s' % self.album.target_dir)

        assert os.path.exists(os.path.join(self.album.target_dir, "XXIMGXX-01.jpg"))
        assert os.path.exists(os.path.join(self.album.target_dir, "XXIMGXX-02.jpg"))
        assert os.path.exists(os.path.join(self.album.target_dir, "XXIMGXX-03.jpg"))
        assert os.path.exists(os.path.join(self.album.target_dir, "XXIMGXX-04.jpg"))

    test_get_images.needs_network = True
    test_get_images.needs_authentication = True
    test_get_images_wo_folderjpg.needs_network = True
    test_get_images_wo_folderjpg.needs_authentication = True

class TestTagHandler(TestTaggerUtilFiles):

    def setUp(self):
        TestTaggerUtilFiles.setUp(self)
        self.target_file_name = "test.flac"

    def tearDown(self):
        TestTaggerUtilFiles.tearDown(self)

    def test_tag_single_track(self):
        shutil.copyfile(self.source_file, os.path.join(self.source_dir, self.target_file_name))

        testTagHandler = TagHandler(self.album, self.tagger_config)
        self.album.disc(1).track(1).new_file = self.target_file_name

        testTagHandler.tag_single_track(self.source_dir, self.album.disc(1).track(1))

        metadata = MediaFile(os.path.join(self.source_dir, self.target_file_name))

        assert metadata.artist == "Gigi D'Agostino"
        assert len(metadata.albumartists) == 1
        assert metadata.albumartists == ['Various']
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.year == 2001
        assert metadata.disctotal == 2
        assert metadata.comp
        assert metadata.genres == ["Electronic", "Hip Hop", "Pop", "Rock"]
        assert metadata.freedb_id == "4711"

        # obviously the encoder element is not in the file, but it is returned
        # empty anyway, no need to check this then...
        assert metadata.encoder == None

        # use a different file to check other metadata handling (e.g. artist)
        shutil.copyfile(self.source_file, os.path.join(self.source_dir, self.target_file_name))

        testTagHandler = TagHandler(self.album, self.tagger_config)
        self.album.disc(2).track(19).new_file = self.target_file_name

        testTagHandler.tag_single_track(self.source_dir, self.album.disc(2).track(19))

        metadata = MediaFile(os.path.join(self.source_dir, self.target_file_name))

        logger.debug("artist_sort: %s" % metadata.artist_sort)
        logger.debug("artist: %s" % metadata.artist)
        assert metadata.artist == "D-Flame Feat. Eißfeldt"
        assert metadata.artist_sort == "D-Flame"
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.year == 2001
        assert metadata.disctotal == 2
        assert metadata.disc == 2
        assert metadata.track == 19
        assert metadata.comp
        assert metadata.genres == ["Electronic", "Hip Hop", "Pop", "Rock"]

        # obviously the encoder element is not in the file, but it is returned
        # empty anyway, no need to check this then...
        assert metadata.encoder == None

    def test_tag_album(self):
        self.copy_files(self.album)

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        taggerutils._get_target_list()

        testTagHandler = TagHandler(self.album, self.tagger_config)
        testFileHandler = FileHandler(self.album, self.tagger_config)

        testFileHandler.copy_files()

        testTagHandler.tag_album()

        target_dir = os.path.join(self.target_dir, self.album.target_dir, self.album.disc(1).target_dir)
        metadata = MediaFile(os.path.join(target_dir, "01-gigi_dagostino-la_passion_(radio_cut).flac"))

        assert metadata.artist == "Gigi D'Agostino"
        assert metadata.albumartist == "Various"
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.year == 2001
        assert metadata.disctotal == 2
        assert metadata.comp
        assert metadata.genres == ["Electronic", "Hip Hop", "Pop", "Rock"]

        assert metadata.freedb_id == "4711"

        # obviously the encoder element is not in the file, but it is returned
        # empty anyway, no need to check this then...
        assert metadata.encoder == None

        metadata = MediaFile(os.path.join(target_dir, "20-papa_roach-last_resort_(album_version_explizit).flac"))

        logger.debug("artist: %s" % metadata.artist_sort)
        assert metadata.artist == "Papa Roach"
        assert metadata.artist_sort == "Papa Roach"
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.year == 2001
        assert metadata.disctotal == 2
        assert metadata.disc == 1
        assert metadata.track == 20
        assert metadata.comp
        assert metadata.genres == ["Electronic", "Hip Hop", "Pop", "Rock"]

        # obviously the encoder element is not in the file, but it is returned
        # empty anyway, no need to check this then...
        assert metadata.encoder == None

    def test_tag_album_with_specific_track_artists(self):
        self.ogsrelid = "112146"

        # construct config with only default values
        tagger_config = TaggerConfig(os.path.join(parentdir, "test/empty.conf"))

        dummy_response = TestDummyResponse(self.ogsrelid)
        discogs_album = DummyDiscogsAlbum(dummy_response)
        self.album = discogs_album.map()

        self.copy_files(self.album)

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        taggerutils._get_target_list()

        testTagHandler = TagHandler(self.album, self.tagger_config)
        testFileHandler = FileHandler(self.album, self.tagger_config)

        testFileHandler.copy_files()

        testTagHandler.tag_album()

        target_dir = os.path.join(self.target_dir, self.album.target_dir, self.album.disc(1).target_dir)
        metadata = MediaFile(os.path.join(target_dir, "01-artful_dodger-re-rewind_the_crowd_say_bo_selecta_(radio_edit).flac"))

        assert metadata.artist == "Artful Dodger"
        assert metadata.albumartist == "Artful Dodger"
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.year == 2000
        assert metadata.disctotal == 2
        assert metadata.genre == "Electronic"

        # obviously the encoder element is not in the file, but it is returned
        # empty anyway, no need to check this then...
        assert metadata.encoder == None

        metadata = MediaFile(os.path.join(target_dir, "04-artful_dodger_feat_romina_johnson-movin_too_fast_(artful_dodger_original_mix).flac"))

        assert metadata.artist == "Artful Dodger Feat. Romina Johnson"
        assert metadata.albumartist == "Artful Dodger"
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.year == 2000
        assert metadata.disctotal == 2
        assert metadata.track == 4
        assert metadata.genre == "Electronic"

        # obviously the encoder element is not in the file, but it is returned
        # empty anyway, no need to check this then...
        assert metadata.encoder == None

        target_dir = os.path.join(self.target_dir, self.album.target_dir, self.album.disc(2).target_dir)
        metadata = MediaFile(os.path.join(target_dir, "20-paul_johnson-get_get_down_(illicit_remix).flac"))

        assert metadata.artist == "Paul Johnson"
        assert metadata.albumartist == "Artful Dodger"
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.year == 2000
        assert metadata.disctotal == 2
        assert metadata.disc == 2
        assert metadata.track == 20
        assert metadata.genre == "Electronic"

        # obviously the encoder element is not in the file, but it is returned
        # empty anyway, no need to check this then...
        assert metadata.encoder == None

    def test_tag_album_wo_country(self):
        self.ogsrelid = "543030"

        # construct config with only default values
        tagger_config = TaggerConfig(os.path.join(parentdir, "test/empty.conf"))

        dummy_response = TestDummyResponse(self.ogsrelid)
        discogs_album = DummyDiscogsAlbum(dummy_response)
        self.album = discogs_album.map()

        # copy file to source directory and rename it
        self.copy_files_single_album(11)

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        taggerutils._get_target_list()

        testTagHandler = TagHandler(self.album, self.tagger_config)
        testFileHandler = FileHandler(self.album, self.tagger_config)

        testFileHandler.copy_files()

        testTagHandler.tag_album()

        target_dir = os.path.join(self.target_dir, self.album.target_dir)
        metadata = MediaFile(os.path.join(target_dir, "01-front_242-masterhit.flac"))

        assert metadata.artist == "Front 242"
        assert metadata.albumartist == "Front 242"
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.year == 1992
        assert metadata.disctotal == 1
        assert metadata.genre == "Electronic"

        # obviously the encoder element is not in the file, but it is returned
        # empty anyway, no need to check this then...
        assert metadata.encoder == None

        assert metadata.country == ""

    def test_tag_single_album_with_video_tracks(self):
        self.ogsrelid = "13748"

        # construct config with only default values
        tagger_config = TaggerConfig(os.path.join(parentdir, "test/empty.conf"))

        dummy_response = TestDummyResponse(self.ogsrelid)
        discogs_album = DummyDiscogsAlbum(dummy_response)
        self.album = discogs_album.map()

        # copy file to source directory and rename it
        self.copy_files_single_album(7)

        taggerutils = TaggerUtils(self.source_dir, self.target_dir, self.tagger_config, self.album)

        taggerutils._get_target_list()

        testTagHandler = TagHandler(self.album, self.tagger_config)
        testFileHandler = FileHandler(self.album, self.tagger_config)

        testFileHandler.copy_files()

        testTagHandler.tag_album()

        target_dir = os.path.join(self.target_dir, self.album.target_dir)
        metadata = MediaFile(os.path.join(target_dir, "01-coldcut-timber_(chopped_down_radio_edit).flac"))

        assert metadata.artist == "Coldcut"
        assert metadata.albumartists == ["Coldcut", "Hexstatic"]
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.year == 1998
        assert metadata.disctotal == 1
        assert metadata.genre == "Electronic"
        assert metadata.tracktotal == 7

        # obviously the encoder element is not in the file, but it is returned
        # empty anyway, no need to check this then...
        assert metadata.encoder == None

        assert metadata.country == "Canada"

        metadata = MediaFile(os.path.join(target_dir, "07-coldcut-timber_(the_cheech_wizards_polythump_requiem_for_the_ancient_forests_mix).flac"))

        assert metadata.artist == "Coldcut"
        assert metadata.albumartists == ["Coldcut", "Hexstatic"]
        assert metadata.discogs_id == self.ogsrelid
        assert metadata.tracktotal == 7
