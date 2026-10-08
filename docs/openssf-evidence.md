# OpenSSF Best Practices evidence: SetupHelper

This index supports review against the [OpenSSF Passing criteria](https://www.bestpractices.dev/en/criteria/0). It is not an awarded badge, a security guarantee or a completed self-attestation. Initial source inventory: `ab756e69f861d48e6bf5af4c3f7816e1df30431f`. Re-check the final merged commit and its CI before submitting an assessment.

## Project and contribution process

Installs, reinstalls, updates and removes add-on packages on Venus OS.

- [Public repository and history](https://github.com/victron-venus/SetupHelper) provide source, commits and interim changes.
- [README](../ReadMe.md) describes installation, configuration and usage.
- [Contribution process](../CONTRIBUTING.md) documents reports, review, style and the policy to add automated tests for major changes.
- [Issues](https://github.com/victron-venus/SetupHelper/issues) and [pull requests](https://github.com/victron-venus/SetupHelper/pulls) provide searchable public discussion and change review.
- [Security policy](../SECURITY.md) documents confidential reporting, response goals, trust boundaries and delivery practices.

A root project license is missing; upstream licensing must be resolved. Do not claim the FLOSS-license criteria are met.

## Implementation and interfaces

- [PackageManager.py](../PackageManager.py)
- [setup](../setup)
- [PackageDevelopmentGuidelines.md](../PackageDevelopmentGuidelines.md)

Interface documentation must explain accepted configuration and inputs, outputs, failure handling and relevant permission boundaries. Verify it against the implementation when changing behavior; source links alone do not establish that every interface is documented.

## Build, test and analysis evidence

No automated application test suite is documented in this checkout; this is an unresolved Passing prerequisite.

[GitHub Actions](https://github.com/victron-venus/SetupHelper/actions) provides run logs and results. The checked-in workflow definitions are:

- [coderabbit-review.yml](../.github/workflows/coderabbit-review.yml)
- [dependency-review.yml](../.github/workflows/dependency-review.yml)
- [latest-tag.yml](../.github/workflows/latest-tag.yml)
- [scorecards.yml](../.github/workflows/scorecards.yml)

Do not equate a green metadata or release job with successful application tests. Record actual test results, coverage limitations and security-analysis results for the submitted revision. Test execution does not establish physical-device behavior.

## Items requiring explicit verification before submission

- Confirm the private reporting channel works and examine issue/advisory history. Historical response-time claims require actual reports and responses, including any reports outside GitHub.
- Obtain primary-developer attestations about secure-design and vulnerability-prevention knowledge; repository text cannot establish a person's knowledge.
- Verify every user-facing release has useful release notes and upgrade impact, and includes any assigned vulnerability identifiers for fixes.
- Review dependency, code-scanning and secret-scanning findings and their age. A workflow success result is not proof that all findings are resolved.
- Review the actual cryptographic libraries, protocols, key lengths, randomness, certificate checks and password storage applicable to this project. Do not copy another project's answers.
- Verify build reproducibility from source, test policy adherence in recent substantive changes, dynamic analysis and any manual-memory-code checks.
- Link only this project's real awarded badge once the assessment is accepted.

The live assessment, when created, is the source of truth for the badge level. Unverified criteria remain open.
