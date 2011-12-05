# nbpkg - a Python library for RPM Packagers
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

import os
import re

import git

import pyrpkg

import cli

class Commands(pyrpkg.Commands):
    def __init__(self, path, lookaside, lookasidehash, lookaside_cgi,
            gitbaseurl, anongiturl, branchre, remote, kojiconfig,
            build_client, user=None, dist=None, target=None):
        """Init the object and some configuration details.

        We need to overload this to add our own attributes and properties.
        """
        super(Commands, self).__init__(path, lookaside, lookasidehash,
                lookaside_cgi, gitbaseurl, anongiturl, branchre, remote,
                kojiconfig, build_client, user, dist, target)

        # New properties
        self._fedora_remote = None

    # -- Overloaded property loaders -----------------------------------------
    def load_rpmdefines(self):
        """Populate rpmdefines based on branch data.

        We need to overload this as we don't use the same branch names.
        """
        # We only match the top level branch name exactly.
        # Anything else is too dangerous and --dist should be used
        if re.match(r'nb\d\.\d$', self.branch_merge):
            # E.g: 'networkbox/nb5.0'
            self.distval = self.branch_merge.split('nb')[1]
            self.distvar = 'nbrs'
            self.dist = 'nb%s' % self.distval

        elif re.match(r'nbplayground$', self.branch_merge):
            # E.g: 'networkbox-nonfree/nbplayground'
            self.distval = self._findmasterbranch()
            self.distvar = 'nbrs'
            self.dist = 'nb%s' % self.distval

        elif re.match(r'nb-fedora\d\d$', self.branch_merge):
            raise NotImplementedError("Can't handle the local Fedora branch "+\
                    "just yet, ask Mathieu to implement it.")

        elif re.match(r'nb-master$', self.branch_merge):
            raise NotImplementedError("Can't handle the local Fedora branch "+\
                    "just yet, ask Mathieu to implement it.")

        elif re.match(r'nb-rhel\d$', self.branch_merge):
            self.distval = self.branch_merge.split('nb-rhel')[1]
            self.distvar = 'rhel'
            self.dist = 'el%s' % self.distval
            self.mockconfig = 'epel-%s-%s' % (self.distval, self.localarch)

        elif re.match(r'nb-epel\d$', self.branch_merge):
            self.distval = self.branch_merge.split('nb-epel')[1]
            self.distvar = 'rhel'
            self.dist = 'el%s' % self.distval
            self.mockconfig = 'epel-%s-%s' % (self.distval, self.localarch)

        else:
            raise pyrpkg.rpkgError('Could not find the dist from branch name '
                                   '%s\nPlease specify with --dist' %
                                   self.branch_merge)

        short_distval = self.distval.replace('.', '')

        self._rpmdefines = ["--define '_sourcedir %s'" % self.path,
                            "--define '_specdir %s'" % self.path,
                            "--define '_builddir %s'" % self.path,
                            "--define '_srcrpmdir %s'" % self.path,
                            "--define '_rpmdir %s'" % self.path,
                            "--define 'dist .%s'" % self.dist,
                            "--define '%s %s'" % (self.distvar, short_distval),
        # Note: Contrary to Fedora, we do not define the following:
        #                   "--define '%s 1'" % self.dist,
        # This is because it is completely broken in our case, because our
        # dist is 'nb5.0', and rpm chokes on the dot when evaluating the macro.
        # It becomes a choice between having a defined value that will never
        # work or not having it defined at all, and I chose the the latter to
        # avoid confusion (we never even tried to use it anyway).
                            ]

    def load_target(self):
        """This creates the target attribute based on branch merge"""
        branch = self.branch_merge
        freeness = 'nonfree' if ('nonfree' in self.remote) else 'free'

        self._target = '%s-%s-candidate' % (branch, freeness)

    # -- New properties ------------------------------------------------------
    @property
    def fedora_remote(self):
        """Return the remote object associated with the Fedora dist-git."""
        if not self._fedora_remote:
            self.load_fedora_remote()
        return self._fedora_remote

    def load_fedora_remote(self):
        """Search if we already have a fedora remote."""
        for remote in self.repo.remotes:
            # FIXME: Don't hard-code those values, get the fedpkg config
            if remote.name == 'fedora':
                self._fedora_remote = remote
                break

        else:
            # We finished iterating without finding a Fedora remote
            # FIXME: Don't hard-code those values, get the fedpkg config
            self._fedora_remote = self.repo.create_remote('fedora',
                    'git://pkgs.fedoraproject.org/%s' % self.module_name)

    # -- Overloaded features -------------------------------------------------
    def push(self):
        """Push changes to the remote repository"""
        # First check that we are not pushing to Fedora
        # FIXME: Ugly screen scraping
        push_remote = self.repo.git.config('--get',
                'branch.%s.remote' % self.branch_merge)
        if push_remote != self.remote:
            raise pyrpkg.rpkgError('Can only push to the Network Box ' + \
                    'infrastructure')

        # Then only push the relevant branches on the appropriate remote
        cmd = ['git', 'push', self.remote]

        # FIXME: Ugly screen scraping, functional programming style
        merged = map(lambda x: x.strip(),
                     filter(lambda x: re.match(self.branchre, x),
                            git.Git().branch('--merged',
                                             self.repo.active_branch.name
                                             ).split()))

        if not merged:
            raise pyrpkg.rpkgError('Could not find any local branch to push')

        cmd.extend(merged)
        self._run_command(cmd, cwd=self.path)

    # -- New features --------------------------------------------------------
    def _findmasterbranch(self):
        """Find the right "nbrs" for master"""

        # Create a list of "nbrses"
        nbrses = []

        # Create a regex to find branches that exactly match nb#.#.  Should not
        # catch branches such as nb5.0-foobar
        branchre = r'nb\d\.\d$'

        # Find the repo refs
        for ref in self.repo.refs:
            # Only find the remote refs
            if type(ref) == git.refs.RemoteReference:
                # Search for branch name by splitting off the remote
                # part of the ref name and returning the rest.  This may
                # fail if somebody names a remote with / in the name...
                if re.match(branchre, ref.name.split('/', 1)[1]):
                    # Add just the simple nb#.# part to the list
                    nbrses.append(ref.name.split('/')[1])

        if nbrses:
            # Sort the list...
            nbrses.sort()

            # ... so we can take the last one and strip it from its 'nb'...
            latest_distval = nbrses[-1].strip('nb')

            # ... then split it into two integers...
            tokens = latest_distval.split('.')

            # ... so we can add 1 to the last one and recreate the new dist
            return "%s.%s" % (tokens[0], (int(tokens[1])+1))

        else:
            #
            # This is what we should do, once we have Koji
            #
            # We may not have NBRSes. Find out what experimental target does.
            try:
                experimentaltarget = self.anon_kojisession.getBuildTarget(self.target)
            except:
                # We couldn't hit koji, bail.
                raise pyrpkg.rpkgError('Unable to query koji to find \
                                       experimental target')
            desttag = experimentaltarget['dest_tag_name']
            return desttag.replace('nb', '')

    def retire(self, message=None):
        """Delete all tracked files and commit a new dead.package file

        Use optional message in commit.

        Runs the commands and returns nothing

        This is a copy-paste from fedpkg. Changes here must be examined and
        eventually pushed upstream.
        """

        cmd = ['git', 'rm', '-rf', '.']
        self._run_command(cmd, cwd=self.path)

        if not message:
            message = 'Package is retired'

        fd = open(os.path.join(self.path, 'dead.package'), 'w')
        fd.write(message + '\n')
        fd.close()

        cmd = ['git', 'add', os.path.join(self.path, 'dead.package')]
        self._run_command(cmd, cwd=self.path)

        self.commit(message=message)

    def fetchfedora(self):
        """Synchronise with the Fedora dist-git module."""
        self.fedora_remote.fetch('--no-tags')
