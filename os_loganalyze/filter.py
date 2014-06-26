#!/usr/bin/python
#
# Copyright (c) 2013 IBM Corp.
# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re

# which logs support severity
SUPPORTS_SEV = re.compile(
    '(screen-(n-|c-|q-|g-|h-|ir-|ceil|key|sah)'  # openstack screen logs
    '|tempest\.txt|syslog)')  # other things we understand

SYSLOGDATE = '\w+\s+\d+\s+\d{2}:\d{2}:\d{2}'
DATEFMT = '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}((\.|\,)\d{3})?'
STATUSFMT = '(DEBUG|INFO|WARNING|ERROR|TRACE|AUDIT)'

OSLO_LOGMATCH = '^(?P<date>%s)(?P<line>(?P<pid> \d+)? (?P<status>%s).*)' % \
    (DATEFMT, STATUSFMT)
SYSLOG_MATCH = ('^(?P<date>%s)(?P<line> (?P<host>[\w\-]+) '
                '(?P<service>\S+):.*)' %
                (SYSLOGDATE))

OSLORE = re.compile(OSLO_LOGMATCH)
SYSLOGRE = re.compile(SYSLOG_MATCH)

SEVS = {
    'NONE': 0,
    'DEBUG': 1,
    'INFO': 2,
    'AUDIT': 3,
    'TRACE': 4,
    'WARNING': 5,
    'ERROR': 6
    }


class LogLine(object):
    status = "NONE"
    line = ""
    date = ""
    pid = ""
    service = ""

    def __init__(self, line, old_sev="NONE"):
        self._parse(line, old_sev)

    def _syslog_status(self, service):
        if service in ('tgtd', 'proxy-server'):
            return 'DEBUG'
        else:
            return 'INFO'

    def _parse(self, line, old_sev):
        m = OSLORE.match(line)
        if m:
            self.status = m.group('status')
            self.line = m.group('line')
            self.date = m.group('date')
            self.pid = m.group('pid')
            return
        m = SYSLOGRE.match(line)
        if m:
            self.service = m.group('service')
            self.line = m.group('line')
            self.date = m.group('date')
            self.status = self._syslog_status(self.service)
            return

        self.status = old_sev
        self.line = line


class Filter(object):

    def __init__(self, fname, generator, minsev="NONE"):
        self.minsev = minsev
        self.gen = generator
        self.supports_sev = SUPPORTS_SEV.search(fname) is not None
        self.fname = fname

    def __iter__(self):
        old_sev = "NONE"
        for line in self.gen:
            logline = LogLine(line, old_sev)
            if self.supports_sev and self.skip_by_sev(logline.status):
                old_sev = logline.status
                continue

            old_sev = logline.status
            yield logline.date + logline.line

    def skip_by_sev(self, sev):
        """should we skip this line?

        If the line severity is less than our minimum severity,
        yes we should.
        """
        minsev = self.minsev
        return SEVS.get(sev, 0) < SEVS.get(minsev, 0)
