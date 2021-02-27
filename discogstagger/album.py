import logging

logger = logging


class BaseObject(object):

    pass


class Track(BaseObject):
    """ A disc contains several tracks, each track has a tracknumber,
        a title, an artist """

    def __init__(self, tracknumber, title, artists):
        self.tracknumber = tracknumber
        self.title = title
        self.artists = artists
        self.discsubtitle = None
        self.mediatype = None
        self.filename = None

    @property
    def artist(self):
        return self.artists[0]

    def __getattr__(self, name):
        return None


class Disc(BaseObject):
    """ An album has one or more discs, each disc has a number and
        could have also a disctitle, furthermore several tracks
        are on each disc """

    def __init__(self, discnumber):
        self.discnumber = discnumber
        self.discsubtitle = None
        self.mediatype = None
        self.tracks = []
        self.filetype = None

    def track(self, trackno):
        return self.tracks[trackno - 1]


class Album(BaseObject):
    """ An album contains one or more discs and has a title, an artist
        (special case: Various), a source identifier (eg. discogs_id)
        and a catno """

    def __init__(self, identifier, title, artists):
        self.id = identifier
        self.artists = artists
        self.title = title
        self.discs = []
        self.fileformat = "flac"
        self.genres = []
        self.styles = []

    @property
    def has_multi_disc(self):
        return len(self.discs) > 1

    def disc(self, discno):
        return self.discs[discno - 1]

    @property
    def artist(self):
        return self.artists[0]

    @property
    def genre(self):
        return ';'.joint(self.genres)

    @property
    def style(self):
        try:
            return ';'.joint(self.styles)
        except KeyError:
            return None

    def __getattr__(self, name):
        return None
