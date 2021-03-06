# -*- coding: utf-8 -*-

# Copyright (C) 2013-2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import instance_of
from hamcrest import only_contains
from six import StringIO, text_type
from unittest import TestCase

from xivo.unicode_csv import UnicodeDictReader, UnicodeDictWriter


class TestUnicodeDictReader(TestCase):

    def test_read_utf8(self):
        csv_data = ['firstname,lastname', 'Père,Noël', 'fírstnámé,lástnámé']
        reader = UnicodeDictReader(csv_data, delimiter=',')
        expected_result = [
            {
                'firstname': u'Père',
                'lastname': u'Noël'
            },
            {
                'firstname': u'fírstnámé',
                'lastname': u'lástnámé'
            }
        ]

        results = [result for result in reader]

        assert_that(results, equal_to(expected_result))
        for result in results:
            assert_that(result.keys(), only_contains(instance_of(text_type)))
            assert_that(result.values(), only_contains(instance_of(text_type)))

    def test_read_utf8_with_superfluous_fields(self):
        csv_data = ['firstname,lastname', 'Père,Noël,et,son,renne,Léon', 'fírstnámé,lástnámé']
        reader = UnicodeDictReader(csv_data, delimiter=',')
        expected_result = [
            {
                'firstname': u'Père',
                'lastname': u'Noël',
                None: ['et', 'son', 'renne', u'Léon'],
            },
            {
                'firstname': u'fírstnámé',
                'lastname': u'lástnámé'
            }
        ]

        results = [result for result in reader]

        assert_that(results, equal_to(expected_result))

    def test_read_utf8_with_missing_fields(self):
        csv_data = ['firstname,lastname', 'Père', 'fírstnámé,lástnámé']
        reader = UnicodeDictReader(csv_data, delimiter=',')
        expected_result = [
            {
                'firstname': u'Père',
                'lastname': None,
            },
            {
                'firstname': u'fírstnámé',
                'lastname': u'lástnámé'
            }
        ]

        results = [result for result in reader]

        assert_that(results, equal_to(expected_result))


class TestUnicodeDictWriter(TestCase):

    def test_writerow_utf8(self):
        first_row = {
            'firstname': u'Père',
            'lastname': u'Noël'
        }
        second_row = {
            'firstname': u'fírstnámé',
            'lastname': u'lástnámé'
        }
        expected_result = 'Père,Noël\r\nfírstnámé,lástnámé\r\n'
        result = StringIO()
        fieldnames = ['firstname', 'lastname']
        writer = UnicodeDictWriter(result, fieldnames=fieldnames)

        writer.writerow(first_row)
        writer.writerow(second_row)

        assert_that(result.getvalue(), equal_to(expected_result))

    def test_writerows_utf8(self):
        first_row = {
            'firstname': u'Père',
            'lastname': u'Noël'
        }
        second_row = {
            'firstname': u'fírstnámé',
            'lastname': u'lástnámé'
        }
        expected_result = 'Père,Noël\r\nfírstnámé,lástnámé\r\n'
        result = StringIO()
        fieldnames = ['firstname', 'lastname']
        writer = UnicodeDictWriter(result, fieldnames=fieldnames)

        writer.writerows((first_row, second_row))

        assert_that(result.getvalue(), equal_to(expected_result))
