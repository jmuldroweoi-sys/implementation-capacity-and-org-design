# Negative fixtures

Deliberately invalid inputs. `tests/test_validate.py` copies the repository into a temporary folder, injects one fixture, and asserts that the matching validator check fails. These files are never read by the calculator and never published as data. All content is synthetic data and an illustrative example of what the validator must reject.
