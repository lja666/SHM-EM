# Author Actions Before Public Submission

These publication metadata and independent validation decisions cannot be
inferred from source code.

- Confirm whether the six named authors or their institution hold the software
  and public-artifact copyright; update `LICENSE.txt` and `DATA_LICENSE.txt` if
  the institutional determination differs. Add ORCIDs when available.
- Add the archive DOI after the GitHub `v1.0.0` release is deposited in Zenodo
  or an equivalent long-term archive.
- Add the SoftwareX article DOI after assignment.
- Add training provenance, split strategy, metrics, and limitations if the
  manuscript claims predictive performance rather than software integration.
- Check that manuscript counts, endpoint names, screenshots, input/output
  hashes, and terminology match release 1.0.0.
- Run `scripts/reproduce-local.ps1` on a clean Windows machine and retain the
  JSON acceptance output with the submission record.
- Generate a wheelhouse or hash-locked Python requirements file if the archive
  policy requires individual wheel hashes. The current lock fixes versions and
  records the validated runtime.

The six model bundles and `src/frontend/public/pit-point-layout.png` are
authorized for public inclusion. The complete research dataset is not public
and must remain outside the repository and release archive.

Do not commit `.env`, `src/pit_pre/config.json`, database passwords, SMTP
credentials, map-provider keys, or any restricted SQL export.
