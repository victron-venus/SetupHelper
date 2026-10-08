# Contributing to SetupHelper

Installs, reinstalls, updates and removes add-on packages on Venus OS.

## Reports and discussion

Use [GitHub Issues](https://github.com/victron-venus/SetupHelper/issues) for bugs, enhancements and design discussion. Search existing reports first. English reports and pull requests are welcome. Include the version or commit, platform, sanitized configuration, reproduction steps, expected behavior and actual behavior. Do not include credentials, personal data or private capture files. Use [SECURITY.md](SECURITY.md) for confidential vulnerability reports.

## Proposing a change

1. Fork or clone the repository over HTTPS and create a topic branch from the default branch.
2. Keep the change focused and explain the problem and observable behavior in a pull request.
3. Follow the existing language style and checked-in formatter/linter configuration. Resolve new warnings; explain any narrowly scoped exception with evidence.
4. Add automated tests for major new functionality and regression tests for corrected bugs. Cover rejected input, unavailable dependencies and relevant failure paths as well as successful input.
5. Update user-facing configuration/interface documentation and release notes for changed behavior. Record upgrade impact and any public vulnerability identifier when applicable.
6. Report the exact checks run, their results and any checks that were not run. Wait for required CI and reviewer approval before merging.

Changes retain the licensing terms of the files they modify. This fork lacks a clear root license; maintainers must resolve upstream licensing before representing the whole project as FLOSS.

## Local validation

Review [PackageDevelopmentGuidelines.md](PackageDevelopmentGuidelines.md) before changing package installation behavior. This checkout has no documented automated application test suite. Do not treat a passing repository metadata workflow as an installation or recovery test; record isolated-device validation explicitly.

Automated tests use mocks or controlled fixtures where available. A passing unit test does not establish hardware safety. Describe any physical-device test separately, including firmware, configuration and expected rollback. Never run installation, deployment, Terraform apply or actuator commands merely to validate a documentation change.

## Source and interfaces

- [PackageManager.py](PackageManager.py)
- [setup](setup)
- [PackageDevelopmentGuidelines.md](PackageDevelopmentGuidelines.md)

See [ReadMe.md](ReadMe.md) for acquisition, configuration and usage, and [the evidence index](docs/openssf-evidence.md) for the public development-process references.
