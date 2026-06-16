"""Offline tests for date parsing (no OpenAI API key required)."""

import unittest

from history_agent.dateparse import DateParseError, parse_date_input


class ParseFullDateTests(unittest.TestCase):
    def test_day_month_year_words(self):
        d = parse_date_input("7 July 1984")
        self.assertEqual((d.day, d.month, d.year), (7, 7, 1984))
        self.assertTrue(d.has_year)

    def test_ordinal_suffix(self):
        d = parse_date_input("7th July 1984")
        self.assertEqual((d.day, d.month, d.year), (7, 7, 1984))

    def test_iso_format(self):
        d = parse_date_input("1969-07-20")
        self.assertEqual((d.day, d.month, d.year), (20, 7, 1969))

    def test_slashes_dayfirst(self):
        d = parse_date_input("07/08/1984")
        self.assertEqual((d.day, d.month, d.year), (7, 8, 1984))

    def test_human_and_slug_with_year(self):
        d = parse_date_input("7 July 1984")
        self.assertEqual(d.human(), "7th July 1984")
        self.assertEqual(d.slug(), "1984-07-07")


class ParseDayMonthOnlyTests(unittest.TestCase):
    def test_day_month_no_year(self):
        d = parse_date_input("21 July")
        self.assertEqual((d.day, d.month), (21, 7))
        self.assertIsNone(d.year)
        self.assertFalse(d.has_year)

    def test_month_day_order(self):
        d = parse_date_input("July 21")
        self.assertEqual((d.day, d.month), (21, 7))
        self.assertIsNone(d.year)

    def test_ordinal_no_year(self):
        d = parse_date_input("21st July")
        self.assertEqual((d.day, d.month), (21, 7))

    def test_human_and_slug_without_year(self):
        d = parse_date_input("21 July")
        self.assertEqual(d.human(), "21st July")
        self.assertEqual(d.slug(), "july-21")

    def test_leap_day_allowed_without_year(self):
        d = parse_date_input("29 February")
        self.assertEqual((d.day, d.month), (29, 2))


class InvalidInputTests(unittest.TestCase):
    def test_empty(self):
        with self.assertRaises(DateParseError):
            parse_date_input("   ")

    def test_year_only_is_ambiguous(self):
        with self.assertRaises(DateParseError):
            parse_date_input("1984")

    def test_month_only_is_ambiguous(self):
        with self.assertRaises(DateParseError):
            parse_date_input("July")

    def test_impossible_day(self):
        with self.assertRaises(DateParseError):
            parse_date_input("31 February 1999")

    def test_gibberish(self):
        with self.assertRaises(DateParseError):
            parse_date_input("not a date")


if __name__ == "__main__":
    unittest.main()
