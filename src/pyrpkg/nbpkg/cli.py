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
        self.parser.add_argument('--nonfree', action='store_true',
                                 help='Interact with the nonfree modules ' \
                                      'we build')

        self.setup_nb_subparsers()

    def setup_nb_subparsers(self):
        """Register the Network Box specific targets."""
        self.register_fetchfedora()
        self.register_newsourcesfedora()
        self.register_retire()
        self.register_sourcesfedora()

    # -- New targets ---------------------------------------------------------
    # --- First register them ---
    def register_fetchfedora(self):
        """Register the fetchfedora command."""
        fetchfedora_parser = self.subparsers.add_parser('fetchfedora',
                help='Get changes from Fedora',
                description='This will fetch the history of the module in \
                        Fedora, adding the remote if necessary.')
        fetchfedora_parser.set_defaults(command=self.fetchfedora)

    def register_newsourcesfedora(self):
        """Register the new-sources-fedora command."""
        new_sources_fedora_parser = self.subparsers.add_parser(
                "new-sources-fedora",
                help="Upload new sourcefiles to the Fedora lookaside cache",
                description="This will upload new source files to the Fedora"
                            "lookaside cache and remove any existing files. "
                            "The sources and .gitignore files will be updated"
                            " for the new file(s).")
        new_sources_fedora_parser.add_argument("files", nargs="+")
        new_sources_fedora_parser.set_defaults(command=self.new_sources_fedora,
                                               replace=True)

    def register_retire(self):
        """Register the retire target"""

        retire_parser = self.subparsers.add_parser('retire',
                                              help='Retire a package',
                                              description='This command will \
                                              remove all files from the repo \
                                              and leave a dead.package file.')
        retire_parser.add_argument('-p', '--push',
                                   default=False,
                                   action='store_true',
                                   help='Push changes to remote repository')
        retire_parser.add_argument('msg',
                                   nargs='?',
                                   help='Message for retiring the package')
        retire_parser.set_defaults(command=self.retire)

    def register_sourcesfedora(self):
        """Register the sourcesfedora command."""
        sourcesfedora_parser = self.subparsers.add_parser('sourcesfedora',
                help='Get sources from the Fedora lookaside cache',
                description='This command will obtain the files listed as ' \
                            'SourceX in the spec file, but instead of using' \
                            ' the configured lookaside URL, it will use the' \
                            ' Fedora one.')
        sourcesfedora_parser.set_defaults(command=self.sourcesfedora)

    # --- Then implement them ---
    def fetchfedora(self):
        try:
            self.cmd.fetchfedora()
        except Exception, e:
            self.log.error('Could not run fetchfedora: %s' % e)
            sys.exit(1)

    def new_sources_fedora(self):
        # This is all mostly copy-pasted from pyrpkg.rpkgCli.new_sources(),
        # except for the lines clearly marked as being different.
        #
        # Make sure to keep it all in sync!

        # Check to see if the files passed exist
        for file in self.args.files:
            if not os.path.isfile(file):
                raise Exception('Path does not exist or is '
                                'not a file: %s' % file)

        # -- This is the only difference with pyrpkg.rpkgCli.new_sources() ---
        self.cmd.upload_fedora(self.args.files, replace=self.args.replace)

        self.log.info("Source upload succeeded. Don't forget to commit the "
                      "sources file")

    def retire(self):
        try:
            self.cmd.retire(self.args.msg)
        except Exception, e:
            self.log.error('Could not retire package: %s' % e)
            sys.exit(1)

        if self.args.push:
            self.push()

    def sourcesfedora(self):
        try:
            self.cmd.sourcesfedora()
        except Exception, e:
            self.log.error('Could not run sourcesfedora: %s' % e)
            sys.exit(1)

    # -- Overloaded targets --------------------------------------------------
    def clone(self):
        """Overload the rpkg method, to remove anonymous clone."""
        if self.args.branches:
            self.log.error("Just no.")
            sys.exit(1)

        super(nbpkgClient, self).clone()

    def push(self):
        # TODO: this could be submitted to rpkg
        try:
            self.cmd.push()
        except Exception, e:
            self.log.error('Could not push: %s' % e)
            sys.exit(1)


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
