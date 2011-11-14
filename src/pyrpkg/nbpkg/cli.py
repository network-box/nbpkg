# cli.py - a cli client class module for fedpkg
#
# Copyright (C) 2011 Network Box Corporation Limited
# Author(s): Mathieu Bridon <mathieu.bridon@network-box.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
# the full text of the license.
#
# This program is based on the GPLv2+-licensed fedpkg library by Jesse Keating:
#     https://fedorahosted.org/fedora-packager

from pyrpkg.cli import cliClient
import sys
import os
import logging


class nbpkgClient(cliClient):
    def __init__(self, config, name='nbpkg'):
        super(nbpkgClient, self).__init__(config, name)

        # Handle the free/nonfree modules
        self.parser.add_argument('-z', '--nonfree', action='store_true', help='Interact with the nonfree modules we build')

        self.setup_nb_subparsers()

    def setup_nb_subparsers(self):
        """Register the Network Box specific targets."""
        self.register_fetchfedora()

    # -- New targets ---------------------------------------------------------
    # --- First register them ---
    def register_fetchfedora(self):
        """Register the fetchfedora command."""
        fetchfedora_parser = self.subparsers.add_parser('fetchfedora',
                help='Get changes from Fedora',
                description='This will fetch the history of the module in \
                        Fedora, adding the remote if necessary.')
        fetchfedora_parser.set_defaults(command=self.fetchfedora)

    # --- Then implement them ---
    def fetchfedora(self):
        try:
            self.cmd.fetchfedora()
        except Exception, e:
            self.log.error('Could not run fetchfedora: %s' % e)
            sys.exit(1)

    # -- Overloaded targets --------------------------------------------------
    def push(self):
        # TODO: this could be submitted to rpkg
        try:
            self.cmd.push()
        except Exception, e:
            self.log.error('Could not push: %s' % e)
            sys.exit(1)

######################################################################
# FIXME: Deploy Koji/Bodhi, remove this function to use the rpkg one #
######################################################################
    def _watch_koji_tasks(self, *args, **kwargs):
        pass
######################################################################

if __name__ == '__main__':
    client = nbpkgClient()
    client._do_imports()
    client.parse_cmdline()

    if not client.args.path:
        try:
            client.args.path = os.getcwd()
        except:
            print('Could not get current path, have you deleted it?')
            sys.exit(1)

    # setup the logger -- This logger will take things of INFO or DEBUG and
    # log it to stdout.  Anything above that (WARN, ERROR, CRITICAL) will go
    # to stderr.  Normal operation will show anything INFO and above.
    # Quiet hides INFO, while Verbose exposes DEBUG.  In all cases WARN or
    # higher are exposed (via stderr).
    log = client.site.log
    client.setupLogging(log)

    if client.args.v:
        log.setLevel(logging.DEBUG)
    elif client.args.q:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)

    # Run the necessary command
    try:
        client.args.command()
    except KeyboardInterrupt:
        pass
