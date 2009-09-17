"""Helper functions for XIVO

Copyright (C) 2008-2009  Proformatique

"""

__version__ = "$Revision$ $Date$"
__license__ = """
    Copyright (C) 2008-2009  Proformatique

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import re
import sys
import logging

from xivo import ConfigDict

from xivo import anysql
from xivo.BackSQL import backsqlite
from xivo.BackSQL import backmysql

log = logging.getLogger("xivo.xivo_helpers")

AGI_CONFFILE = "/etc/pf-xivo/agid.conf"

find_asterisk_pattern_char = re.compile('[[NXZ!.]').search

def position_of_asterisk_pattern_char(ast_pattern):
    mo = find_asterisk_pattern_char(ast_pattern)
    if not mo:
        return None
    return mo.start()

def clean_extension(exten):
    """
    Return an extension from an Asterisk extension pattern.
    """
    if exten is None:
        return ""

    exten = str(exten)

    if exten.startswith('_'):
        exten = exten[1:]
        e = position_of_asterisk_pattern_char(exten)
        if e is not None:
            exten = exten[:e]
    
    return exten

def split_extension(exten):
    """
    Return a list of strings that compose the multi parts of an
    extension as to be generated by unsplit_extension().

    >>> split_extension('**142***2666**2***3#**3')
    ('*42', '*666*', '*#*')
    """
    flag = 0
    ret = []
    cur = ""
    i = 1

    if not isinstance(exten, str):
        raise ValueError, "exten argument must be a string"

    for x in exten:
        if flag == 2:
            if x.isdigit():
                x = int(x)
                if x == i:
                    flag = 0
                    cur += '*'
                else:
                    raise ValueError, "Wrong digit: %d, excepted: %d" % (x, i)
            elif x == '*':
                ret.append(cur)
                cur = ""
                i += 1
            else:
                raise ValueError, "Wrong value: %r, excepted digit or asterisk!" % x
        elif x == '*':
            flag += 1
        elif flag == 1:
            flag = 0
            ret.append(cur)
            cur = x
            i += 1
        else:
            cur += x
    else:
        ret.append(cur)

    return tuple(ret)

def unsplit_extension(xlist):
    """
    Compute and return an extension from multi extensions.

    >>> unsplit_extension(('*98','666'))
    '**198*666'
    """
    ret = []
    cur = ""

    if not isinstance(xlist, (tuple, list)):
        raise ValueError, "Argument must be a tuple or list"

    for i, x in enumerate(xlist):
        i += 1
        for c in x:
            if c == '*':
                cur += "**%d" % i
            else:
                cur += c
        else:
            ret.append(cur)
            cur = ""

    return '*'.join(ret)

def fkey_extension(xleft, xlist):
    components = []

    xleft = clean_extension(xleft)

    for x in xlist:
        x = clean_extension(x)

        if x:
            components.append(x)

    return xleft + unsplit_extension(components)

def speed_dial_key_components(xleft, xright, fkext, monitoringext, isbsfilter):
    """
    Return a list of strings that compose the different parts of an
    extension as to be generated by speed_dial_key_extension()
    """
    if xleft:
        xleft = clean_extension(xleft)
    else:
        xleft = ""
    components = [xleft]
    if xright and fkext:
        raise ValueError, "(xright, fkext) == " + `(xright, fkext)` + " but both shall not be set"
    elif xright:
        right_part = str(xright)
    elif fkext:
        right_part = str(fkext)
    else:
        right_part = ""
    if isbsfilter:
        if (not right_part) or (not monitoringext):
            raise ValueError, "isbsfilter and ((not right_part) or (not monitoringext))"
        monitoringext = str(monitoringext)
        if right_part <= monitoringext:
            components.extend([right_part, '*', monitoringext])
        else:
            components.extend([monitoringext, '*', right_part])
    elif right_part:
        components.append(str(right_part))
    return components

def speed_dial_key_extension(xleft, xright, fkext, monitoringext = None, isbsfilter = False):
    """
    Compute and return an extension that can be affected to a speed dial
    key.  Behave as a mathematical function.

    Input of this function is mostly the result of derefencing the content
    of the 'phonefunckey' XIVO table.  Each line in this table contains
    references to entities that identify the purpose of one speed dial key.
    This function transforms the partial strings associated to each entity
    so that a unique extension is generated (for a given user) that can be
    called to trigger the corresponding function.

    xleft is optional and describes the operation.  If it evaluates to
    False the returned extension is simply designed to identify the wanted
    entity.  It can be passed in either xright or fkext (the missing one
    being set to None) but not both.  The difference between xright and
    fkext is really an issue of the caller.  When xleft is significant, it
    typically is an Asterisk extension pattern, in which a left part must
    be constant.  This left part describes the wanted opearation (for
    example activation of unconditional forwarding).  In this case, the
    right part of the extension references the object entity needed to
    complete the description of the action: for example an extension to
    which the forwarding must take place.  It is passed in xright or fkext
    but not both.  In some cases, the action does not need any object, and
    both xright and fkext will be set to None.

    There is a special mode of operation (but even considering it, this
    function still keeps its mathematical definition): when isbsfilter is
    True, the "boss secretary filter" feature is addressed.  In this case,
    the filter entity that is addressed needs two callable extensions to be
    uniquely referenced.  One will come from the now classic xright or
    fkext alternative (one and only one must be significant in this case).
    The other is simply passed in monitoringext (which is not used if
    isbsfilter is False).  The two extensions are then arbitrarily ordered
    so that there exists a well defined bijection between the addressed
    filter and its symbolic extension based generated reference, separated
    by an asterisk '*' and appended to the function identifier.

    xleft - None or a string that is either an extension or an Asterisk
            extension pattern.
            If it is an Asterisk extension pattern -- that is, the first
            character is an underscore '_' -- then the shortest variable
            right part of the string will be stripped.
            For example:
                "_5."                => "5"
                "_[5-7]."            => ""
                "_666[3-689]XNZ!"    => "666"
                "_42!XNZ!666[5-7]Z." => "42"
                "42"                 => "42"
            The stripped xleft will be the left part of the generated
            extension.
    xright - None or a string that will be the right part of the generated
             extension.
    fkext - like xright
    monitoringext - The monitoring extension, only significant if
                    isbsfilter is True.
    isbsfilter - If False, xleft is stripped and xright or fkext is
                 appended to the result to form the string to be returned.
                 If True, A*B will be appended to the stripped xleft with
                 A <= B where (A,B) is a permutation of (C, monitoringext),
                 and C is xright or fkext (the one that is a string) or an
                 empty string (only one of xright or fkext can be
                 significant).
                 A and B are compared using the lexicographic order.

    WARNING: xright and fkext shall not be both not None.

    WARNING: The form of extension patterns is not checked.  The first
    variable specifying character is simply detected using the '[[NXZ!.]'
    regular expression.  Everything from this character to the end in the
    extension pattern is then dismissed in order to keep the constant left
    part of the pattern.
    """
    return ''.join(c for c in speed_dial_key_components(
                                  xleft, xright, fkext,
                                  monitoringext, isbsfilter)
                     if c)

db_conn = None

def abort(message, show_tb=False):
    """
    Log @message at critical level (including a backtrace
    if @show_tb is true) then exit.
    """
    log.critical(message, exc_info=show_tb)
    sys.exit(1)

def db_connect():
    """DataBase CONNECT

    This function is a simple wrapper to connect to the database with error
    handling.  If successful, it returns the connection object.  Otherwise
    execution is aborted.

    This module keeps a reference to the connection created, so the users
    are permitted to call this function like :

    cursor = xivo_helpers.db_connect().cursor()

    If a previous connection was open when this function is called, its
    changes are committed and the connection is closed before creating a
    new one.
    """
    global db_conn
    db_close()
    db_uri = ConfigDict.ReadSingleKey(AGI_CONFFILE, 'db', 'db_uri')

    try:
        db_conn = anysql.connect_by_uri(db_uri)
    except:
        abort("Unable to connect to %s" % db_uri, show_tb=True)

    return db_conn

def db_close():
    global db_conn
    if db_conn:
        db_conn.commit()
        db_conn.close()
        db_conn = None
