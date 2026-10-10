# Playbook — verified biography portraits

Run `hath0r portraits sync --config cfg/portraits.yaml` to mine and checkpoint without database writes. Review the JSONL report. Add `--apply` to write verified results; add `--resume` to reuse a completed checkpoint in the same run directory. Dry-run factory execution performs no requests or writes. Revalidate in a fresh run directory on later syncs.

