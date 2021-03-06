#!/usr/bin/env python  # noqa
# -*- coding: utf-8 -*-

"""Scarlett Exceptions Module."""


class ScarlettError(Exception):
    """General ScarlettOS exception occurred."""

    pass


class InvalidEntityFormatError(ScarlettError):
    """When an invalid formatted entity is encountered."""

    pass


class NoEntitySpecifiedError(ScarlettError):
    """When no entity is specified."""

    pass


class TemplateError(ScarlettError):
    """Error during template rendering."""

    def __init__(self, exception):
        """Initalize the error."""
        super().__init__('{}: {}'.format(exception.__class__.__name__,
                                         exception))


class DecodeError(Exception):
    """The base exception class for all decoding errors raised by this package."""


class NoBackendError(DecodeError):
    """The file could not be decoded by any backend. Either no backends are available or each available backend failed to decode the file."""


class GStreamerError(DecodeError):
    """Something went terribly wrong with Gstreamer."""
    pass


class UnknownTypeError(GStreamerError):
    """Raised when Gstreamer can't decode the given file type."""

    def __init__(self, streaminfo):
        super(UnknownTypeError, self).__init__(
            "can't decode stream: " + streaminfo
        )
        self.streaminfo = streaminfo


class FileReadError(GStreamerError):
    """Raised when the file can't be read at all."""
    pass


class NoStreamError(GStreamerError):
    """Raised when the file was read successfully but no audio streams
    were found.
    """

    def __init__(self):
        super(NoStreamError, self).__init__('no audio streams found')


class MetadataMissingError(GStreamerError):
    """Raised when GStreamer fails to report stream metadata (duration,
    channels, or sample rate).
    """
    pass


class IncompleteGStreamerError(GStreamerError):
    """Raised when necessary automations of GStreamer (namely, the
    principal plugin packages) are missing.
    """

    def __init__(self):
        super(IncompleteGStreamerError, self).__init__(
            'missing GStreamer base plugins'
        )


class InvalidUri(GStreamerError):
    """Raised when the file was read successfully but no audio streams
    were found.
    """

    def __init__(self):
        super(InvalidUri, self).__init__('Invalid uri provided for audio source')


class UriDoesNotExist(GStreamerError):
    """Raised when Uri audio does not exist.
    """

    def __init__(self):
        super(UriDoesNotExist, self).__init__('Uri does not exist on file system')


class UriReadError(GStreamerError):
    """Raised when Uri audio does not exist.
    """

    def __init__(self):
        super(UriReadError, self).__init__('Uri can not be read from file system')


class MainRunnerError(Exception):
    pass


class MainRunnerAbortedError(MainRunnerError):
    pass


class MainRunnerTimeoutError(MainRunnerError):
    pass


class SubProcessError(Exception):
    pass


class TimeOutError(Exception):
    pass
