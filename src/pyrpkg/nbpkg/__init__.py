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
# This program is based on the GPLv2+-licensed rpkg library by Jesse Keating:
#     https://fedorahosted.org/rpkg

import os
import re

import git

import pyrpkg

import cli

class Commands(pyrpkg.Commands):
    def __init__(self, path, lookaside, lookasidehash, lookaside_cgi,
            gitbaseurl, anongiturl, branchre, remote, kojiconfig,
            build_client,
            # -- nbpkg-specific arguments ------------------------------------
            fedora_lookaside, fedora_lookaside_cgi, fedora_kojiconfig,
            fedora_anongiturl,
            # -- end of nbpkg-specific arguments -----------------------------
            user=None, dist=None, target=None, quiet=False):
        """Init the object and some configuration details.

        We need to overload this to add our own attributes and properties.
        """
        super(Commands, self).__init__(path, lookaside, lookasidehash,
                lookaside_cgi, gitbaseurl, anongiturl, branchre, remote,
                kojiconfig, build_client, user, dist, target, quiet)

        # New attributes
        self.fedora_lookaside = fedora_lookaside
        self.fedora_lookaside_cgi = fedora_lookaside_cgi
        self.fedora_kojiconfig = fedora_kojiconfig
        self.fedora_anongiturl = fedora_anongiturl

        # New properties
        self._cert_file = None
        self._ca_cert = None
        self._freedom = None

        # To interact with the Fedora infrastructure
        self._fedora_remote = None
        self._fedora_cert_file = None
        self._fedora_ca_cert = None

    # -- Overloaded property loaders -----------------------------------------
    def load_rpmdefines(self):
        """Populate rpmdefines based on branch data.

        We need to overload this as we don't use the same branch names.
        """
        # We only match the top level branch name exactly.
        # Anything else is too dangerous and --dist should be used
        if re.match(r'nb\d\.\d$', self.branch_merge):
            # E.g: 'networkbox/nb5.0'
            self._distval = self.branch_merge.split('nb')[1]
            self._distvar = 'nbrs'
            self.dist = 'nb%s' % self.distval

        elif re.match(r'nbplayground$', self.branch_merge):
            # E.g: 'networkbox-nonfree/nbplayground'
            self._distval = self._findmasterbranch()
            self._distvar = 'nbrs'
            self.dist = 'nb%s' % self.distval

        elif re.match(r'nb-fedora\d\d$', self.branch_merge):
            self._distval = self.branch_merge.split("nb-fedora")[1]
            self._distvar = "fedora"
            self.dist = "fc%s" % self.distval
            self.mockconfig = "fedora-%s-%s" % (self._distval, self.localarch)

        elif re.match(r'nb-rhel\d$', self.branch_merge):
            self._distval = self.branch_merge.split('nb-rhel')[1]
            self._distvar = 'rhel'
            self.dist = 'el%s' % self.distval
            self.mockconfig = 'epel-%s-%s' % (self.distval, self.localarch)

        elif re.match(r'nb-epel\d$', self.branch_merge):
            self._distval = self.branch_merge.split('nb-epel')[1]
            self._distvar = 'rhel'
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
        freeness = 'free' if self.freedom else 'nonfree'

        self._target = '%s-%s-candidate' % (branch, freeness)

    # -- New properties ------------------------------------------------------
    @property
    def cert_file(self):
        """This property ensures the cert_file attribute

        This is shamelessly copy-pasted from fedpkg.
        Contribute any changes back upstream.
        """
        if not self._cert_file:
            self.load_cert_files()
        return self._cert_file

    @property
    def ca_cert(self):
        """This property ensures the ca_cert attribute

        This is shamelessly copy-pasted from fedpkg.
        Contribute any changes back upstream.
        """
        if not self._ca_cert:
            self.load_cert_files()
        return self._ca_cert

    def load_cert_files(self):
        """This loads the cert_file attribute"""
        import ConfigParser

        with open(self.kojiconfig) as f:
            config = ConfigParser.ConfigParser()
            config.readfp(f)

            if not config.has_section(os.path.basename(self.build_client)):
                raise pyrpkg.rpkgError("Can't find the [%s] section in the "
                                       "Koji config" % self.build_client)

            self._cert_file = os.path.expanduser(config.get(self.build_client,
                                                            "cert"))
            self._ca_cert = os.path.expanduser(config.get(self.build_client,
                                                          "serverca"))

    @property
    def fedora_cert_file(self):
        """This property ensures the fedora_cert_file attribute"""

        if not self._fedora_cert_file:
            self.load_fedora_cert_files()
        return self._fedora_cert_file

    @property
    def fedora_ca_cert(self):
        """This property ensures the fedora_ca_cert attribute"""

        if not self._fedora_ca_cert:
            self.load_fedora_cert_files()
        return self._fedora_ca_cert

    def load_fedora_cert_files(self):
        """This loads the fedora_cert_file and fedora_ca_cert attributes"""
        import ConfigParser

        with open(self.fedora_kojiconfig) as f:
            config = ConfigParser.ConfigParser()
            config.readfp(f)

            if not config.has_section(os.path.basename(self.build_client)):
                raise pyrpkg.rpkgError("Can't find the [%s] section in the "
                                       "Koji config" % self.build_client)

            self._fedora_cert_file = os.path.expanduser(
                                config.get(self.build_client, "cert"))
            self._fedora_ca_cert = os.path.expanduser(
                                config.get(self.build_client, "serverca"))

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
            try:
                module_name = self.module_name
            except pyrpkg.rpkgError, e:
                # This happens when we don't have a spec file yet (e.g merging
                # from Fedora for the first time)
                module_name = os.path.basename(self.path)

            self._fedora_remote = self.repo.create_remote('fedora',
                    self.fedora_anongiturl % {"module": module_name})

    @property
    def freedom(self):
        if not self._freedom:
            self.load_freedom()
        return self._freedom

    def load_freedom(self):
        if "nonfree" in self.remote:
            self._freedom = False
        else:
            self._freedom = True

    # -- Overloaded features -------------------------------------------------
    def clone(self, module, path=None, branch=None, bare_dir=None, anon=False):
        """Clone a repo, optionally check out a specific branch.

        This overloads the pyrpkg method, to always checkout the 'nbplayground'
        branch by default.
        """
        if not branch:
            branch = 'nbplayground'

        super(Commands, self).clone(module, path, branch, bare_dir, anon)

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

        # Move the active branch to the end, so that merged upstream branches
        # get pushed first
        if self.repo.active_branch.name in merged:
            merged.remove(self.repo.active_branch.name)
            merged.append(self.repo.active_branch.name)

        if not merged:
            raise pyrpkg.rpkgError('Could not find any local branch to push')

        cmd.extend(merged)
        self._run_command(cmd, cwd=self.path)

    def sources(self, outdir=None, lookasideurl=None):
        """Fetch sources from a lookaside cache.

        We overload it to allow fetching from a different lookaside cache than
        the configured one.
        """
        if lookasideurl:
            self.lookaside = lookasideurl

        # Don't pass that additional parameter to our parent
        super(Commands, self).sources(outdir=outdir)

    def _create_curl(self):
        """Common curl setup options used for all requests to lookaside.

        This is shamelessly copy-pasted from fedpkg.
        Contribute any changes back upstream.
        """
        import pycurl

        # Overloaded to add cert files to curl objects
        # Call the super class
        curl = super(Commands, self)._create_curl()

        # Set the user's certificate:
        if os.path.exists(self.cert_file):
            curl.setopt(pycurl.SSLCERT, self.cert_file)
        else:
            self.log.warn("Missing certificate: %s" % self.cert_file)

        # Set the CA certificate:
        if os.path.exists(self.ca_cert):
            curl.setopt(pycurl.CAINFO, self.ca_cert)
        else:
            self.log.warn("Missing certificate: %s" % self.ca_cert)

        return curl

    def _do_curl(self, file_hash, file):
        """Use curl manually to upload a file

        This is shamelessly copy-pasted from fedpkg.
        Contribute any changes back upstream.
        """
        # This is overloaded to add in the user's cert
        cmd = ['curl', '-k', '--cert', self.cert_file, '--fail', '-o',
               '/dev/null', '--show-error', '--progress-bar', '-F',
               'name=%s' % self.module_name, '-F', 'md5sum=%s' % file_hash,
               '-F', 'file=@%s' % file]
        if self.quiet:
            cmd.append('-s')
        cmd.append(self.lookaside_cgi)
        self._run_command(cmd)

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
            # We may not have NBRSes. Find out what experimental target does.
            try:
                experimentaltarget = self.anon_kojisession.getBuildTarget(self.target)
            except:
                # We couldn't hit koji, bail.
                raise pyrpkg.rpkgError("Unable to query koji to find " \
                                       "experimental target")
            desttag = experimentaltarget['dest_tag_name']

            # Remove the trailing '-free' or '-nonfree'
            desttag = desttag.split('-')[0]

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

    def upload_fedora(self, files, replace=False):
        pass

    def sourcesfedora(self):
        """Fetch sources from the Fedora lookaside cache."""
        self.sources(lookasideurl=self.fedora_lookaside)
