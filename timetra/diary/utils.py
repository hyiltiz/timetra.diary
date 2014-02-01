# -*- coding: utf-8 -*-
#
#    Timetra is a time tracking application and library.
#    Copyright © 2010-2014  Andrey Mikhaylenko
#
#    This file is part of Timetra.
#
#    Timetra is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Timetra is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Timer.  If not, see <http://gnu.org/licenses/>.
#
"""
Utility functions
=================
"""
from datetime import date, datetime, time, timedelta
import re


try:
    basestring
except NameError:
    # Python3
    basestring = str


def to_date(obj):
    if isinstance(obj, datetime):
        return obj.date()
    if isinstance(obj, date):
        return obj
    raise TypeError('expected date or datetime, got {0}'.format(obj))


def to_datetime(obj):
    if isinstance(obj, datetime):
        return obj
    if isinstance(obj, date):
        return datetime.combine(obj, time(0))
    raise TypeError('expected date or datetime, got {0}'.format(obj))



# TODO: use  https://bitbucket.org/russellballestrini/ago/src
#        or  https://github.com/tantalor/pretty_timedelta

def format_delta(delta, fmt='{hours}:{minutes}'):
    """ Formats timedelta. Allowed variable names are: `days`, `hours`,
    `minutes`, `seconds`.
    """
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return fmt.format(days=delta.days, hours=hours, minutes=minutes,
                      seconds=seconds)


def split_time(string):
    """ Returns a pair of integers `(hours, minutes)` for given string::

        >>> _split_time('02:15')
        (2, 15)
        >>> _split_time('2:15')
        (2, 15)
        >>> _split_time(':15')
        (0, 15)
        >>> _split_time('15')
        (0, 15)

    """
    def _split(s):
        if ':' in s:
            return s.split(':')
        if len(s) <= 2:
            # "35" -> 00:35
            return 0, s
        return s[:-2], s[-2:]

    return tuple(int(x or 0) for x in _split(string))


def parse_time(string):
    """
    Returns a datetime.time object and a boolean that tells whether given time
    should be substracted from the start time.

        >>> parse_time('20')
        (time(0, 20), False)
        >>> parse_time('-1:35')
        (time(1, 35), True)
        >>> parse_time('now')
        datetime.now().time()
        >>> parse_time('now-5')
        datetime.now().time() - timedelta(minutes=5)

    """
    substract = False

    if string == 'now':
        return datetime.now().time(), substract

    if string.startswith('now-'):
        # "now-150"
        now = datetime.now()
        _, substring = string.split('-')
        delta, _ = parse_time(substring)
        start = now - timedelta(hours=delta.hour, minutes=delta.minute)
        return start.time(), substract

    if string.startswith('-'):
        # "-2:58"
        substract = True
        string = string[1:]

    hours, minutes = split_time(string)

    return time(hours, minutes), substract


def parse_time_to_datetime(string, relative_to=None, ensure_past_time=True):
    """ Parses string to a datetime, relative to given date (or current one):

    CURRENT FORMAT:
        12:05 = DATE, at 12:05
    TODO:
         1205 = DATE, at 12:05
          205 = DATE, at 02:05
           05 = DATE, at 00:05
            5 = DATE, at 00:05
           -5 = DATE - 5 minutes
    """
    if not string:
        return
    base_date = relative_to or datetime.now()
    parsed_time, _ = parse_time(string)
    date_time = datetime.combine(base_date, parsed_time)

    # microseconds are not important but may break the comparison below
    base_date = base_date.replace(microsecond=0)
    date_time = date_time.replace(microsecond=0)

    if ensure_past_time and base_date < date_time:
        return date_time - timedelta(days=1)
    else:
        return date_time


def parse_delta(string):
    """ Parses string to timedelta.
    """
    if not string:
        return
    hours, minutes = split_time(string)
    return timedelta(hours=hours, minutes=minutes)


def extract_date_time_bounds(spec):
    rx_time = r'[0-9]{0,2}:?[0-9]{1,2}'
    rx_rel = r'[+-]\d+'
    rx_component = r'{time}|{rel}'.format(time=rx_time, rel=rx_rel)
    rx_separator = r'\.\.'
    rxs = tuple(re.compile(x) for x in [
        # all normal cases
        r'(?P<since>{component}){sep}(?P<until>{component})'.format(
            component=rx_component, sep=rx_separator),
        # ultrashortcut "1230+5"
        r'(?P<since>{time})(?P<until>\+\d+)'.format(time=rx_time),
        # ultrashortcut "+5" / "-5"
        r'(?P<since>{rel})'.format(rel=rx_rel),
    ])
    for rx in rxs:
        match = rx.match(spec)
        if match:
            return match.groupdict()
    raise ValueError(u'Could not parse "{}" to time bounds '.format(spec))


def normalize_component(value):
    assert isinstance(value, basestring)

    if value.startswith(('+', '-')):
        hours, minutes = split_time(value[1:])
        assert minutes <= 60
        delta = timedelta(hours=hours, minutes=minutes)
        return delta if value[0] == '+' else -delta
    else:
        hours, minutes = split_time(value)
        return time(hour=hours, minute=minutes)


def normalize_group(last, since, until, now):
    assert since or last
    assert until or now

    if not since:
        since = last
    if not until:
        until = now

    class Lazy:
        def __init__(self, value, func):
            self.func = func
            self.value = value

        def __call__(self, other_value):
            return self.func(self.value, other_value)

    if not isinstance(since, datetime):
        if isinstance(since, time):
            if since < now.time():
                # e.g. since 20:00, now is 20:30, makes sense
                reftime = now
            else:
                # e.g. since 20:50, now is 20:30 → can't be today;
                # probably yesterday (allowing earlier dates can be confusing)
                reftime = now - timedelta(days=1)
            since = reftime.replace(hour=since.hour, minute=since.minute)
            # in any case this must be after the last known fact
            assert last <= since
        elif isinstance(since, timedelta):
            if since.total_seconds() < 0:
                # negative delta: until - delta
                since = Lazy(since, lambda _since, _until: _until + _since)
            else:
                since = last + since

    if not isinstance(until, datetime):
        if isinstance(until, time):
            until = now.replace(hour=until.hour, minute=until.minute)
        elif isinstance(until, timedelta):
            if until.total_seconds() < 0:
                until = now + until    # actually it's kind of "now-5"
            else:
                until = since + until

    # XXX drop the `Lazy` class if `until` really doesn't need it
    if isinstance(since, Lazy):
        since = since(until)

    assert since < until

    return since, until


def parse_date_time_bounds(spec):
    groups = extract_date_time_bounds(spec)

    since = groups.get('since')
    until = groups.get('until')

    assert since or until
    return since, until
