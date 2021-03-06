#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Scarlett Player module. Uses Gstreamer to output audio."""

# NOTE: THIS IS THE CLASS THAT WILL BE REPLACING scarlett_player.py eventually.
# It is cleaner, more object oriented, and will allows us to run proper tests.
# Also threading.RLock() and threading.Semaphore() works correctly.

#
# There are a LOT of threads going on here, all of them managed by Gstreamer.
# If pyglet ever needs to run under a Python that doesn't have a GIL, some
# locks will need to be introduced to prevent concurrency catastrophes.
#
# At the moment, no locks are used because we assume only one thread is
# executing Python code at a time.  Some semaphores are used to block and wake
# up the main thread when needed, these are all instances of
# threading.Semaphore.  Note that these don't represent any kind of
# thread-safety.

from __future__ import with_statement, division, absolute_import

import os
import sys

import signal
import threading
import logging
import pprint

from scarlett_os.internal.gi import gi
from scarlett_os.internal.gi import GObject
from scarlett_os.internal.gi import GLib
from scarlett_os.internal.gi import Gst
from scarlett_os.internal.gi import Gio

from scarlett_os.exceptions import IncompleteGStreamerError
from scarlett_os.exceptions import MetadataMissingError
from scarlett_os.exceptions import NoStreamError
from scarlett_os.exceptions import FileReadError
from scarlett_os.exceptions import UnknownTypeError
from scarlett_os.exceptions import InvalidUri
from scarlett_os.exceptions import UriReadError

import queue
from urllib.parse import quote

from scarlett_os.utility.gnome import trace
from scarlett_os.utility.gnome import abort_on_exception
from scarlett_os.utility.gnome import _IdleObject

from scarlett_os.internal.path import uri_is_valid
from scarlett_os.internal.path import isReadable
from scarlett_os.internal.path import path_from_uri
from scarlett_os.internal.path import get_parent_dir
from scarlett_os.internal.path import mkdir_if_does_not_exist
from scarlett_os.internal.path import fname_exists
from scarlett_os.internal.path import touch_empty_file

# Alias
gst = Gst

# global pretty print for debugging
pp = pprint.PrettyPrinter(indent=4)

logger = logging.getLogger(__name__)


# Constants
QUEUE_SIZE = 10
BUFFER_SIZE = 10
SENTINEL = '__GSTDEC_SENTINEL__'
SEMAPHORE_NUM = 0


# Managing the Gobject main loop thread.

_shared_loop_thread = None
_loop_thread_lock = threading.RLock()


def get_loop_thread():
    """Get the shared main-loop thread.
    """
    global _shared_loop_thread
    with _loop_thread_lock:
        if not _shared_loop_thread:
            # Start a new thread.
            _shared_loop_thread = MainLoopThread()
            _shared_loop_thread.start()
        return _shared_loop_thread

# NOTE: doc updated via https://github.com/Faham/emophiz/blob/15612aaf13401201100d67a57dbe3ed9ace5589a/emotion_engine/dependencies/src/sensor_lib/SensorLib.Tobii/Software/tobiisdk-3.0.2-Win32/Win32/Python26/Modules/tobii/sdk/mainloop.py


class MainLoopThread(threading.Thread):
    """A daemon thread encapsulating a Gobject main loop.

    A mainloop is used by all asynchronous objects to defer handlers and callbacks to. The function run() blocks until the function quit() has been called (and all queued handlers have been executed). The run() function will then execute all the handlers in order.
    """

    def __init__(self):
        super(MainLoopThread, self).__init__()
        self.loop = GObject.MainLoop()
        self.daemon = True

    def run(self):
        self.loop.run()


class ScarlettPlayer(_IdleObject):
    # Anything defined here belongs to the class itself
    #
    # :param path: (str) path to sound file.
    # :handler_error: (callable)
    # :callback: (callable)

    DEFAULT_SRC = 'uridecodebin'

    DEFAULT_SINK = 'pulsesink'

    def __init__(self, path, handle_error, callback):
        self.running = False
        self.finished = False
        self.handle_error = False if handle_error is None else handle_error
        self.callback = callback
        # self.delay_start = False if delay_start is None else delay_start
        # self.stopme = threading.Event()

        # Set up the Gstreamer pipeline.
        # NOTE: Need to add .new for some reason to pass tests ...
        # source: https://github.com/hadware/gstreamer-python-player/issues/1
        self.pipeline = Gst.Pipeline.new('main-pipeline')
        self.ready_sem = threading.Semaphore(SEMAPHORE_NUM)

        # Register for bus signals.
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self._message)
        bus.connect("message::error", self._message)
        bus.connect("message::state-changed", self._on_state_changed)

        # 1. Create pipeline's elements
        self.source = Gst.ElementFactory.make("uridecodebin", 'input_stream')
        self.audioconvert = Gst.ElementFactory.make('audioconvert', None)
        self.splitter = Gst.ElementFactory.make("tee", 'splitter')

        if (not self.source or not self.audioconvert or not self.splitter):
            logger.error("ERROR: Not all elements could be created.")
            raise IncompleteGStreamerError()

        # TODO: Add a test to check for False / None type before moving forward. Throw AttributeError.

        # 2. Set properties
        uri = 'file://' + quote(os.path.abspath(path))

        # Make sure GST likes the uri
        if not uri_is_valid(uri):
            logger.error("Error: "
                         "Something is wrong with uri "
                         "provided. uri: {}".format(uri))
            raise InvalidUri()

        # Make sure we can actually read the uri
        if not isReadable(path_from_uri(uri)):
            logger.error("Error: Can't read uri:"
                         " {}".format(path_from_uri(uri)))
            raise UriReadError()

        self.source.set_property('uri', uri)

        # 3. Add them to the pipeline
        self.pipeline.add(self.source)
        self.pipeline.add(self.audioconvert)
        self.pipeline.add(self.splitter)

        self.audioconvert.link(self.splitter)

        self.source.connect('source-setup', self._source_setup_cb)

        # 4.a. uridecodebin has a "sometimes" pad (created after prerolling)
        self.source.connect('pad-added', self._decode_src_created)
        self.source.connect('no-more-pads', self._no_more_pads)
        self.source.connect("unknown-type", self._unknown_type)

        #######################################################################
        # QUEUE A
        #######################################################################
        self.queueA = Gst.ElementFactory.make('queue', None)
        # BOSSJONESTEMP # self.audioconvert =
        # Gst.ElementFactory.make('audioconvert', None)
        self.appsink = Gst.ElementFactory.make('appsink', None)
        self.appsink.set_property(
            'caps',
            Gst.Caps.from_string('audio/x-raw, format=(string)S16LE'),
        )
        # TODO set endianness?
        # Set up the characteristics of the output. We don't want to
        # drop any data (nothing is real-time here); we should bound
        # the memory usage of the internal queue; and, most
        # importantly, setting "sync" to False disables the default
        # behavior in which you consume buffers in real time. This way,
        # we get data as soon as it's decoded.
        self.appsink.set_property('drop', False)
        self.appsink.set_property('max-buffers', BUFFER_SIZE)
        self.appsink.set_property('sync', False)

        # The callback to receive decoded data.
        self.appsink.set_property('emit-signals', True)
        self.appsink.connect("new-sample", self._new_sample)

        self.caps_handler = self.appsink.get_static_pad("sink").connect(
            "notify::caps", self._notify_caps
        )

        self.pipeline.add(self.queueA)
        self.pipeline.add(self.appsink)

        self.queueA.link(self.appsink)

        # link tee to queueA
        tee_src_pad_to_appsink_bin = self.splitter.get_request_pad('src_%u')
        logger.debug("Obtained request pad "
                     "Name({}) Type({}) for audio branch.".format(
                     self.splitter.name, self.splitter))
        queueAsinkPad = self.queueA.get_static_pad('sink')
        logger.debug(
            "Obtained sink pad for element ({}) for tee -> queueA.".format(queueAsinkPad))
        tee_src_pad_to_appsink_bin.link(queueAsinkPad)

        #######################################################################
        # QUEUE B
        #######################################################################

        self.queueB = Gst.ElementFactory.make('queue', None)
        self.pulsesink = Gst.ElementFactory.make(ScarlettPlayer.DEFAULT_SINK, None)

        self.pipeline.add(self.queueB)
        self.pipeline.add(self.pulsesink)

        self.queueB.link(self.pulsesink)

        self.queueB_sink_pad = self.queueB.get_static_pad('sink')

        # link tee to queueB
        tee_src_pad_to_appsink_bin = self.splitter.get_request_pad('src_%u')
        logger.debug("Obtained request pad Name({}) Type({}) for audio branch.".format(
            self.splitter.name, self.splitter))
        queueAsinkPad = self.queueB.get_static_pad('sink')
        logger.debug(
            "Obtained sink pad for element ({}) for tee -> queueB.".format(queueAsinkPad))
        tee_src_pad_to_appsink_bin.link(queueAsinkPad)

        # recursively print elements
        self._listElements(self.pipeline)

        #######################################################################

        # Set up the queue for data and run the main thread.
        self.queue = queue.Queue(QUEUE_SIZE)
        # False if handle_error is None else handle_error
        # if loop_thread:
        #     self.thread = loop_thread
        # else:
        #     self.thread = get_loop_thread()

        self.thread = get_loop_thread()

        # This wil get filled with an exception if opening fails.
        self.read_exc = None
        self.dot_exc = None

        # Return as soon as the stream is ready!
        self.running = True
        self.got_caps = False

        # if not self.delay_start:

        # if self.stopme.isSet():
        #         return

        self.pipeline.set_state(Gst.State.PLAYING)
        self.on_debug_activate()
        self.ready_sem.acquire()

        if self.read_exc:
            # An error occurred before the stream became ready.
            self.close(True)
            raise self.read_exc

    # def abort(self):
    #     self.stopme.set()

    def _source_setup_cb(self, discoverer, source):
        logger.debug("Discoverer object: ({})".format(discoverer))
        logger.debug("Source object: ({})".format(source))

    def _on_state_changed(self, bus, msg):
        states = msg.parse_state_changed()
        # To state is PLAYING
        if msg.src.get_name() == "pipeline" and states[1] == 4:
            # TODO: Modify the creation of this path, it should be programatically created
            dotfile = "/home/pi/dev/bossjones-github/scarlett_os/_debug/generator-player.dot"
            pngfile = "/home/pi/dev/bossjones-github/scarlett_os/_debug/generator-player-pipeline.png"  # NOQA

            parent_dir = get_parent_dir(dotfile)

            mkdir_if_does_not_exist(parent_dir)

            if os.access(dotfile, os.F_OK):
                os.remove(dotfile)
            if os.access(pngfile, os.F_OK):
                os.remove(pngfile)

            if not fname_exists(dotfile):
                touch_empty_file(dotfile)

            if not fname_exists(pngfile):
                touch_empty_file(pngfile)

            Gst.debug_bin_to_dot_file(msg.src,
                                      Gst.DebugGraphDetails.ALL, "generator-player")
            os.system('/usr/bin/dot' + " -Tpng -o " + pngfile + " " + dotfile)
            print("pipeline dot file created in " +
                  os.getenv("GST_DEBUG_DUMP_DOT_DIR"))

    def _listElements(self, bin, level=0):
        try:
            iterator = bin.iterate_elements()
            # print iterator
            while True:
                elem = iterator.next()
                if elem[1] is None:
                    break
                logger.debug(level * '** ' + str(elem[1]))
                # uncomment to print pads of element
                self._iteratePads(elem[1])
                # call recursively
                self._listElements(elem[1], level + 1)
        except AttributeError:
            pass

    def _iteratePads(self, element):
        try:
            iterator = element.iterate_pads()
            while True:
                pad = iterator.next()
                if pad[1] is None:
                    break
                logger.debug('pad: ' + str(pad[1]))
        except AttributeError:
            pass

    # NOTE: This function generates the dot file, checks that graphviz in installed and
    # then finally generates a png file, which it then displays
    def on_debug_activate(self):
        dotfile = "/home/pi/dev/bossjones-github/scarlett_os/_debug/generator-player.dot"
        pngfile = "/home/pi/dev/bossjones-github/scarlett_os/_debug/generator-player-pipeline.png"  # NOQA

        parent_dir = get_parent_dir(dotfile)

        mkdir_if_does_not_exist(parent_dir)

        if os.access(dotfile, os.F_OK):
            os.remove(dotfile)
        if os.access(pngfile, os.F_OK):
            os.remove(pngfile)

        if not fname_exists(dotfile):
            touch_empty_file(dotfile)

        if not fname_exists(pngfile):
            touch_empty_file(pngfile)

        Gst.debug_bin_to_dot_file(self.pipeline,
                                  Gst.DebugGraphDetails.ALL, "generator-player")
        os.system('/usr/bin/dot' + " -Tpng -o " + pngfile + " " + dotfile)

    # Gstreamer callbacks.

    def _notify_caps(self, pad, args):
        """The callback for the sinkpad's "notify::caps" signal.
        """
        # The sink has started to receive data, so the stream is ready.
        # This also is our opportunity to read information about the
        # stream.
        logger.debug("pad: {}".format(pad))
        logger.debug("pad name: {} parent: {}".format(
            pad.name, pad.get_parent()))
        logger.debug("args: {}".format(args))
        self.got_caps = True
        info = pad.get_current_caps().get_structure(0)

        # Stream attributes.
        self.channels = info.get_int('channels')[1]
        self.samplerate = info.get_int('rate')[1]

        # Query duration.
        success, length = pad.get_peer().query_duration(Gst.Format.TIME)
        if success:
            self.duration = length / 1000000000
            logger.debug("FILE DURATION: {}".format(self.duration))
        else:
            self.read_exc = MetadataMissingError('duration not available')

        # Allow constructor to complete.
        self.ready_sem.release()

    _got_a_pad = False

    def _decode_src_created(self, element, pad):
        """The callback for GstElement's "pad-added" signal.
        """
        # Decoded data is ready. Connect up the decoder, finally.
        name = pad.query_caps(None).to_string()
        logger.debug("pad: {}".format(pad))
        logger.debug("pad name: {} parent: {}".format(
            pad.name, pad.get_parent()))
        if name.startswith('audio/x-raw'):
            nextpad = self.audioconvert.get_static_pad('sink')
            if not nextpad.is_linked():
                self._got_a_pad = True
                pad.link(nextpad)

    def _no_more_pads(self, element):
        """The callback for GstElement's "no-more-pads" signal.
        """
        # Sent when the pads are done adding (i.e., there are no more
        # streams in the file). If we haven't gotten at least one
        # decodable stream, raise an exception.
        if not self._got_a_pad:
            logger.error(
                "If we haven't gotten at least one decodable stream, raise an exception.")
            self.read_exc = NoStreamError()
            self.ready_sem.release()  # No effect if we've already started.

    def _new_sample(self, sink):
        """The callback for appsink's "new-sample" signal.
        """
        if self.running:
            # FIXME: logger.debug("sink: {}".format(sink))
            # FIXME: logger.debug("sink name: {} parent: {}".format(sink.name, sink.get_parent()))
            # New data is available from the pipeline! Dump it into our
            # queue (or possibly block if we're full).
            buf = sink.emit('pull-sample').get_buffer()
            self.queue.put(buf.extract_dup(0, buf.get_size()))
        return Gst.FlowReturn.OK

    def _unknown_type(self, uridecodebin, decodebin, caps):
        """The callback for decodebin's "unknown-type" signal.
        """
        # This is called *before* the stream becomes ready when the
        # file can't be read.
        streaminfo = caps.to_string()
        if not streaminfo.startswith('audio/'):
            # Ignore non-audio (e.g., video) decode errors.
            return
        logger.error("Ignore non-audio (e.g., video) decode errors.")
        logger.error("streaminfo: {}".format(streaminfo))
        self.read_exc = UnknownTypeError(streaminfo)
        self.ready_sem.release()

    def _message(self, bus, message):
        """The callback for GstBus's "message" signal (for two kinds of
        messages).
        """
        if not self.finished:
            if message.type == Gst.MessageType.EOS:
                # The file is done. Tell the consumer thread.
                self.queue.put(SENTINEL)
                if not self.got_caps:
                    logger.error(
                        "If the stream ends before _notify_caps was called, this is an invalid file.")
                    # If the stream ends before _notify_caps was called, this
                    # is an invalid file.
                    self.read_exc = NoStreamError()
                    self.ready_sem.release()

            elif message.type == Gst.MessageType.ERROR:
                gerror, debug = message.parse_error()
                if 'not-linked' in debug:
                    logger.error('not-linked')
                    self.read_exc = NoStreamError()
                elif 'No such file' in debug:
                    self.read_exc = IOError('resource not found')
                else:
                    self.read_exc = FileReadError(debug)
                self.ready_sem.release()

    # Iteration.
    def next(self):
        # Wait for data from the Gstreamer callbacks.
        val = self.queue.get()
        if val == SENTINEL:
            # End of stream.
            raise StopIteration
        return val

    # For Python 3 compatibility.
    __next__ = next

    def __iter__(self):
        return self

    # Cleanup.
    def close(self, force=False):
        """Close the file and clean up associated resources.

        Calling `close()` a second time has no effect.
        """
        if self.running or force:
            self.running = False
            self.finished = True

            # Unregister for signals, which we registered for above with
            # `add_signal_watch`. (Without this, GStreamer leaks file
            # descriptors.)
            try:
                self.pipeline
            except NameError:
                logger.info("well, self.pipeline WASN'T defined after all!")
            else:
                logger.info("OK, self.pipeline IS defined.")
                self.pipeline.get_bus().remove_signal_watch()

            # Stop reading the file.
            self.source.set_property("uri", None)
            # Block spurious signals.
            self.appsink.get_static_pad("sink").disconnect(self.caps_handler)

            # Make space in the output queue to let the decoder thread
            # finish. (Otherwise, the thread blocks on its enqueue and
            # the interpreter hangs.)
            try:
                self.queue.get_nowait()
            except queue.Empty:
                pass

            # Halt the pipeline (closing file).
            self.pipeline.set_state(Gst.State.NULL)
            logger.info("closing generator_player: {}".format(self))

            # Delete the pipeline object. This seems to be necessary on Python
            # 2, but not Python 3 for some reason: on 3.5, at least, the
            # pipeline gets dereferenced automatically.
            del self.pipeline

    def __del__(self):
        logger.info("delete time")
        self.close()

    # Context manager.
    def __enter__(self):
        logger.info("enter time")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("exit time")
        self.close()
        return self.handle_error


# Smoke test.
if __name__ == '__main__':
    if os.environ.get('SCARLETT_DEBUG_MODE'):
        import faulthandler
        faulthandler.register(signal.SIGUSR2, all_threads=True)

        from scarlett_os.internal.debugger import init_debugger
        from scarlett_os.internal.debugger import set_gst_grapviz_tracing
        init_debugger()
        set_gst_grapviz_tracing()
        # Example of how to use it

    wavefile = [
        '/home/pi/dev/bossjones-github/scarlett_os/static/sounds/pi-listening.wav']
    # ORIG # for path in sys.argv[1:]:
    for path in wavefile:
        path = os.path.abspath(os.path.expanduser(path))
        with ScarlettPlayer(path, False, False) as f:
            print(f.channels)
            print(f.samplerate)
            print(f.duration)
            for s in f:
                pass
                # READ IN BLOCKS # print(len(s), ord(s[0]))
