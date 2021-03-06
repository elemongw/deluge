# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009 Ido Abramovich <ido.deluge@gmail.com>
# Copyright (C) 2009 Andrew Resch <andrewresch@gmail.com>
#
# This file is part of Deluge and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import base64
import os
from urllib import url2pathname
from urlparse import urlparse

from twisted.internet import defer

import deluge.common
import deluge.component as component
from deluge.ui.client import client
from deluge.ui.console.main import BaseCommand


class Command(BaseCommand):
    """Add torrents"""

    def add_arguments(self, parser):
        parser.add_argument("-p", "--path", dest="path", help="download folder for torrent")
        parser.add_argument("torrents", metavar="<torrent>", nargs="+",
                            help="One or more torrent files, URLs or magnet URIs")

    def handle(self, options):
        self.console = component.get("ConsoleUI")

        t_options = {}
        if options.path:
            t_options["download_location"] = os.path.expanduser(options.path)

        def on_success(result):
            if not result:
                self.console.write("{!error!}Torrent was not added: Already in session")
            else:
                self.console.write("{!success!}Torrent added!")

        def on_fail(result):
            self.console.write("{!error!}Torrent was not added: %s" % result)

        # Keep a list of deferreds to make a DeferredList
        deferreds = []
        for torrent in options.torrents:
            if not torrent.strip():
                continue
            if deluge.common.is_url(torrent):
                self.console.write("{!info!}Attempting to add torrent from url: %s" % torrent)
                deferreds.append(client.core.add_torrent_url(torrent, t_options).addCallback(on_success).addErrback(
                    on_fail))
            elif deluge.common.is_magnet(torrent):
                self.console.write("{!info!}Attempting to add torrent from magnet uri: %s" % torrent)
                deferreds.append(client.core.add_torrent_magnet(torrent, t_options).addCallback(on_success).addErrback(
                    on_fail))
            else:
                # Just a file
                if urlparse(torrent).scheme == "file":
                    torrent = url2pathname(urlparse(torrent).path)
                path = os.path.abspath(os.path.expanduser(torrent))
                if not os.path.exists(path):
                    self.console.write("{!error!}%s doesn't exist!" % path)
                    continue
                if not os.path.isfile(path):
                    self.console.write("{!error!}This is a directory!")
                    continue
                self.console.write("{!info!}Attempting to add torrent: %s" % path)
                filename = os.path.split(path)[-1]
                with open(path, "rb") as _file:
                    filedump = base64.encodestring(_file.read())
                deferreds.append(client.core.add_torrent_file(filename, filedump, t_options).addCallback(
                    on_success).addErrback(on_fail))

        return defer.DeferredList(deferreds)

    def complete(self, line):
        return component.get("ConsoleUI").tab_complete_path(line, ext=".torrent", sort="date")
