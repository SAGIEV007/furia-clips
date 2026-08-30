"""Dedicated tests for modules.safe_types.coerce_bool and safe_float."""
from __future__ import annotations

import math

import pytest

from modules.safe_types import coerce_bool, safe_float


class TestCoerceBool:
    def test_none_with_default_false(self):
        assert coerce_bool(None) is False
        assert coerce_bool(None, default=False) is False

    def test_none_with_default_true(self):
        assert coerce_bool(None, default=True) is True

    def test_native_bool(self):
        assert coerce_bool(True) is True
        assert coerce_bool(False) is False

    def test_integers(self):
        assert coerce_bool(0) is False
        assert coerce_bool(1) is True
        assert coerce_bool(-1) is True
        assert coerce_bool(2) is True

    def test_floats(self):
        assert coerce_bool(0.0) is False
        assert coerce_bool(1.0) is True
        assert coerce_bool(-0.0) is False

    def test_non_finite_floats_use_default(self):
        assert coerce_bool(float("inf")) is False
        assert coerce_bool(float("-inf")) is False
        assert coerce_bool(float("nan")) is False
        assert coerce_bool(float("inf"), default=True) is True

    def test_empty_string_uses_default(self):
        assert coerce_bool("") is False
        assert coerce_bool("", default=True) is True

    def test_truthy_strings(self):
        assert coerce_bool("true") is True
        assert coerce_bool("TRUE") is True
        assert coerce_bool("yes") is True
        assert coerce_bool("sim") is True
        assert coerce_bool("1") is True
        assert coerce_bool("on") is True
        assert coerce_bool("enabled") is True

    def test_falsy_strings(self):
        assert coerce_bool("false") is False
        assert coerce_bool("FALSE") is False
        assert coerce_bool("no") is False
        assert coerce_bool("não") is False
        assert coerce_bool("nao") is False
        assert coerce_bool("0") is False
        assert coerce_bool("off") is False
        assert coerce_bool("disabled") is False

    def test_non_standard_strings_are_truthy(self):
        assert coerce_bool("maybe") is True
        assert coerce_bool("auto") is True


class TestSafeFloat:
    def test_none_uses_default(self):
        assert safe_float(None) == 0.0
        assert safe_float(None, default=5.5) == 5.5

    def test_valid_numbers(self):
        assert safe_float(0) == 0.0
        assert safe_float(1) == 1.0
        assert safe_float(3.14) == 3.14
        assert safe_float("-2.5") == -2.5

    def test_invalid_string(self):
        assert safe_float("abc") == 0.0
        assert safe_float("abc", default=7.0) == 7.0

    def test_non_finite_uses_default(self):
        assert safe_float(float("inf")) == 0.0
        assert safe_float(float("-inf")) == 0.0
        assert safe_float(float("nan")) == 0.0
        assert safe_float(float("inf"), default=1.0) == 1.0

    def test_default_is_coerced_to_float(self):
        assert safe_float("invalid", default=5) == 5.0
