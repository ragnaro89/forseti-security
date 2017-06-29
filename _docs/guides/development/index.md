---
title: Development
order: 001
hide:
  left_sidebar: true
---
# {{ page.title }}

## Contributing

We welcome your contributions! Check out our guidelines for
[contributing](https://github.com/GoogleCloudPlatform/forseti-security/blob/master/.github/CONTRIBUTING.md).

## Testing

This page describes how to run tests on your Forseti contributions.

### Executing tests

You can find the unit tests in the top-level `tests/` directory.

To execute tests, run the command below:

  ```bash
  $ python setup.py google_test
  ```

To execute the tests just for a particular module:

  ```bash
  $ python setup.py google_test --test-dir tests/MODULE_NAME
  ```

To run tests for a particular file pattern:

  ```bash
  $ python setup.py google_test --test-module-pattern tests
  ```

### Known issues

The unit tests have a lot of errors about gflags. You can ignore these at this
time.
