#!/usr/bin/python
# nbpkg - a script to interact with the Network Box Packaging system
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
# This program is based on the GPLv2+-licensed fedpkg tool by Jesse Keating:
#     https://fedorahosted.org/fedpkg

import os
import sys
import logging
import ConfigParser
import argparse

import pyrpkg
import nbpkg


def main():
    CONF_ROOT = '/etc/rpkg'
    FREE_CONF = os.path.join(CONF_ROOT, 'nbpkg.conf')
    NONFREE_CONF = os.path.join(CONF_ROOT, 'nbpkg-nonfree.conf')

    # Setup an argparser and parse the known commands to get the config file
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--nonfree', action='store_true',
                        help='Interact with the nonfree modules we build')
    parser.add_argument('--path', default=None,
                        help='Define the directory to work in (defaults to cwd)')
    
    (args, other) = parser.parse_known_args()
    
    # Magically handle the 'nonfree' switch unless the user is asking for help
    # Note: This is quite ugly
    if args.nonfree:
        # The user specified, let's honour his wish
        args.config = NONFREE_CONF
    
    elif 'clone' in other or 'co' in other:
        # Can't autodetect for clone, nonfree has to be specified if necessary
        args.config = FREE_CONF
    
    elif os.path.isdir('.git') or args.path:
        # Try to autodetect, based on the name of the remote
        try:
            import git
            repo_git = git.Repo(args.path)
    
            for remote in repo_git.remotes:
                if "nonfree" in remote.name or \
                   "nonfree" in remote.config_reader.get("url"):
                    args.config = NONFREE_CONF
                    break
    
            else:
                # We never ran the 'break' above
                args.config = FREE_CONF
    
        except Exception, e:
            sys.stderr.write("Could not automatically determine free/nonfree status, aborting.\n")
            sys.stderr.write(str(e)+'\n')
            sys.exit(1)
    
    elif other[-1] in ['--help', '-h', 'help']:
        # Doesn't matter, the user wants some help, so just pick one config
        args.config = FREE_CONF

    else:
        sys.stderr.write("Could not automatically determine free/nonfree status, aborting.\n")
        sys.stderr.write("You probably aren't in a cloned directory or forgot to specify the --path option.\n")
        sys.exit(1)
    
    # Make sure we have a sane config file
    if not os.path.exists(args.config) and not other[-1] in ['--help', '-h', 'help']:
        sys.stderr.write('Invalid config file %s\n' % args.config)
        sys.exit(1)
    
    # Setup a configuration object and read config file data
    config = ConfigParser.SafeConfigParser()
    config.read(args.config)
    
    client = nbpkg.cli.nbpkgClient(config)
    client.do_imports(site='nbpkg')
    client.parse_cmdline()
    
    if not client.args.path:
        try:
            client.args.path=os.getcwd()
        except:
            print('Could not get current path, have you deleted it?')
            sys.exit(1)
    
    # setup the logger -- This logger will take things of INFO or DEBUG and
    # log it to stdout.  Anything above that (WARN, ERROR, CRITICAL) will go
    # to stderr.  Normal operation will show anything INFO and above.
    # Quiet hides INFO, while Verbose exposes DEBUG.  In all cases WARN or
    # higher are exposed (via stderr).
    log = pyrpkg.log
    client.setupLogging(log)
    
    if client.args.v:
        log.setLevel(logging.DEBUG)
    elif client.args.q:
        log.setLevel(logging.WARNING)
    else:
        log.setLevel(logging.INFO)
    
    # We have a logger now, use it to debug the freeness
    log.debug("Using config %s" % args.config)
    
    # Run the necessary command
    try:
        sys.exit(client.args.command())
    except KeyboardInterrupt:
        pass
    except Exception, e:
        log.error('Could not execute %s: %s' % (client.args.command.__name__, e))
        sys.exit(1)

if __name__ == "__main__":
    main()
