from django.http import QueryDict
from django.test import SimpleTestCase

from mydigitalmeal.studies.views import (
    MAX_URL_PARAM_KEYS,
    MAX_URL_PARAM_TOTAL_BYTES,
    MAX_URL_PARAM_VALUE_LENGTH,
    _sanitize_url_parameters,
)


class TestSanitizeUrlParameters(SimpleTestCase):
    """Unit tests for `_sanitize_url_parameters`.

    The sanitizer is the only line of defence against malicious enrolment
    URLs being persisted into ``Participant.extra_data``; each cap getting
    silently broken by a refactor is a real risk, so every cap and drop
    rule has its own test.
    """

    def test_drops_keys_failing_regex(self):
        # 'utm.source' contains '.', non-ASCII keys are rejected, only
        # 'ok_key-1' matches ``^[A-Za-z0-9_\\-]{1,40}$``.
        result = _sanitize_url_parameters(
            QueryDict("utm.source=x&%C3%A9=y&ok_key-1=z"),
        )

        self.assertEqual(result, {"ok_key-1": "z"})

    def test_drops_overlong_keys(self):
        long_key = "a" * 41  # one over the 40-char limit
        result = _sanitize_url_parameters(QueryDict(f"{long_key}=v"))

        self.assertEqual(result, {})

    def test_truncates_long_values(self):
        long_value = "x" * 500
        result = _sanitize_url_parameters(QueryDict(f"k={long_value}"))

        self.assertEqual(len(result["k"]), MAX_URL_PARAM_VALUE_LENGTH)

    def test_caps_key_count(self):
        # 30 short-key/short-value pairs: well under the byte cap, so the
        # key-count cap is the binding constraint.
        query = QueryDict("&".join(f"k{i:03d}=v" for i in range(30)))
        result = _sanitize_url_parameters(query)

        self.assertEqual(len(result), MAX_URL_PARAM_KEYS)

    def test_caps_total_size(self):
        # Use 40-char keys (the regex max) so each pair costs 240 bytes —
        # the total-size cap (4096) then fires at 17 entries, well below
        # the key-count cap (20). This forces the test to exercise the
        # size cap independently of the key-count cap; with shorter keys
        # the two caps coincide and the size-cap assertion is vacuous.
        long_value = "x" * MAX_URL_PARAM_VALUE_LENGTH
        long_key = lambda i: f"{'a' * 37}{i:03d}"  # 40-char unique keys  # noqa: E731
        query = QueryDict(
            "&".join(f"{long_key(i)}={long_value}" for i in range(30)),
        )
        result = _sanitize_url_parameters(query)

        self.assertLess(len(result), MAX_URL_PARAM_KEYS)
        total = sum(len(k) + len(v) for k, v in result.items())
        self.assertLessEqual(total, MAX_URL_PARAM_TOTAL_BYTES)

    def test_preserves_multivalued_as_list(self):
        result = _sanitize_url_parameters(QueryDict("tag=a&tag=b"))

        self.assertEqual(result, {"tag": ["a", "b"]})

    def test_single_value_kept_as_scalar(self):
        result = _sanitize_url_parameters(QueryDict("tag=a"))

        self.assertEqual(result, {"tag": "a"})

    def test_empty_query_returns_empty_dict(self):
        self.assertEqual(_sanitize_url_parameters(QueryDict("")), {})
