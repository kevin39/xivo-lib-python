"""Helper functions for XIVO

Copyright (C) 2008, Proformatique

"""

__version__ = "$Revision$ $Date$"
__license__ = """
    Copyright (C) 2008, Proformatique

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""

import re
import sys
import anysql
import except_tb
import ConfigDict
from BackSQL import backsqlite
from BackSQL import backmysql

AGI_CONFFILE = "/etc/asterisk/xivo_agi.conf"

find_asterisk_pattern_char = re.compile('[[NXZ!.]').search

def position_of_asterisk_pattern_char(ast_pattern):
	mo = find_asterisk_pattern_char(ast_pattern)
	if not mo:
		return None
	return mo.start()

def speed_dial_key_components(xleft, xright, fkext, monitoringext, isbsfilter):
	"""Returns a list of strings that compose the different parts of an
	extension as to be generated by speed_dial_key_extension()
	"""
	if xleft:
		xleft = str(xleft)
		if xleft[0] == '_':
			xleft = xleft[1:]
			e = position_of_asterisk_pattern_char(xleft)
			if e is not None:
				xleft = xleft[:e]
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

def speed_dial_key_extension(xleft, xright, fkext,
                             monitoringext=None, isbsfilter=False):
	"""Computes and returns an extension that can be affected to a speed dial
	key. Behaves as a mathematical function.
	
	Input of this function is mostly the result of derefencing the content
	of the 'phonefunckey' XIVO table. Each line in this table contains
	references to entities that identify the purpose of one speed dial key.
	This function transforms the partial strings associated to each entity
	so that a unique extension is generated (for a given user) that can be
	called to trigger the corresponding function.
	
	xleft is optional and describes the operation. If it evaluates to False
	the returned extension is simply designed to identify the wanted entity.
	It can be passed in either xright or fkext (the missing one being set to
	None) but not both. The difference between xright and fkext is really an
	issue of the caller. When xleft is significant, it typically is an
	Asterisk extension pattern, in which a left part must be constant. This
	left part describes the wanted opearation (for example activation of
	unconditional forwarding). In this case, the right part of the extension
	references the object entity needed to complete the description of the
	action: for example an extension to which the forwarding must take
	place. It is passed in xright or fkext but not both. In some cases, the
	action does not need any object, and both xright and fkext will be set
	to None.
	
	There is a special mode of operation (but even considering it, this
	function still keeps its mathematical definition): when isbsfilter is
	True, the "boss secretary filter" feature is addressed. In this case,
	the filter entity that is addressed needs two callable extensions to be
	uniquely referenced. One will come from the now classic xright or fkext
	alternative (one and only one must be significant in this case). The
	other is simply passed in monitoringext (which is not used if isbsfilter
	is False). The two extensions are then arbitrarily ordered so that there
	exists a well defined bijection between the addressed filter and its
	symbolic extension based generated reference, separated by an asterisk
	'*' and appended to the function identifier.
	
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
	monitoringext - The monitoring extension, only significant if isbsfilter
	                is True.
	isbsfilter - If False, xleft is stripped and xright or fkext is
	             appended to the result to form the string to be returned.
		     If True, A*B will be appended to the stripped xleft with
		     A <= B where (A,B) is a permutation of (C, monitoringext),
		     and C is xright or fkext (the one that is a string) or an
		     empty string (only one of xright or fkext can be
		     significant).
		     A and B are compared using the lexicographic order.
	
	WARNING: xright and fkext shall not be both not None.
	
	WARNING: The form of extension patterns is not checked. The first
	variable specifying character is simply detected using the '[[NXZ!.]'
	regular expression. Everything from this character to the end in the
	extension pattern is then dismissed in order to keep the constant left
	part of the pattern.
	"""
	return ''.join(c for c in speed_dial_key_components(
	                              xleft, xright, fkext,
				      monitoringext, isbsfilter)
	                     if c)

def stderr_write_nl(message):
	sys.stderr.write("%s\n" % message)

output_fn = stderr_write_nl

db_conn = None

def set_output_fn(out_fn):
	output_fn = out_fn

def abort(message, show_tb = False):
	"""Generic abort function
	
	Display a message using the global output_fn function, optionally
	dumping the exception trace, and stop execution.
	
	If show_tb is True, this function must be called from an except block.
	"""

	output_fn(message)

	if show_tb:
		except_tb.log_exception(output_fn)

	sys.exit(1)

def db_connect():
	"""DataBase CONNECT
	
	This function is a simple wrapper to connect to the database with error
	handling. If successful, it returns the connection object. Otherwise
	execution is aborted.
	
	This module keeps a reference to the connection created, so the users
	are permitted to call this function like :
	
	cursor = xivo_helpers.db_connect().cursor()
	
	If a previous connection was open when this function is called, its
	changes are committed and the connection is closed before creating a
	new one.
	"""

	db_close()
	db_uri = ConfigDict.ReadSingleKey(AGI_CONFFILE, 'db', 'db_uri')

	try:
		db_conn = anysql.connect_by_uri(db_uri)
	except:
		abort("Unable to connect to %s" % db_uri, True)

	return db_conn

def db_close():
	if db_conn:
		db_conn.commit()
		db_conn.close()
		db_conn = None

__all__ = ('speed_dial_key_extension', 'speed_dial_key_components')