from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Auditable Access to Opportunity pipeline")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    acquire_parser = commands.add_parser("acquire", help="Follow official links and inspect original files")
    acquire_parser.add_argument("--refresh", action="store_true", help="Recheck release pages and downloads")
    acquire_parser.add_argument("--locked", action="store_true", help="Download exact reviewed inputs from source_lock.json")
    geography_parser = commands.add_parser("geography", help="Acquire complete ONS geography for configured districts")
    geography_parser.add_argument("--update-mappings", action="store_true", help="Record verified geography batches in input mappings")
    inspect_parser = commands.add_parser("inspect", help="Inspect a retained workbook, CSV or archive")
    inspect_parser.add_argument("path", type=Path)
    commands.add_parser("build", help="Validate reviewed mappings, prepare data and run descriptive analysis")
    commands.add_parser("status", help="Show acquisition and reviewed-input status without network access")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "acquire":
        from opportunity.acquire import acquire, replay_lock
        if args.locked:
            if args.refresh:
                parser.error("Use --locked for reproduction or --refresh for discovery, not both")
            replay_lock(root)
        else:
            result = acquire(root, refresh=args.refresh)
            if any(value.get("status") in {"blocked", "failed"} for value in result.values()):
                raise SystemExit("Acquisition incomplete. See reports/acquisition_status.md and metadata/source_register.csv.")
    elif args.command == "geography":
        import yaml
        from opportunity.geography import acquire_geography
        manifest = acquire_geography(root)
        if args.update_mappings:
            path = root / "config/verified_inputs.yml"
            inputs = yaml.safe_load(path.read_text())
            descriptor = lambda record: {"path": record["local_path"], "sha256": record["sha256"], "download_url": record["download_url"]}
            inputs["tables"]["lookup"]["files"] = [descriptor(record) for record in manifest["lookup_records"]]
            inputs["boundaries"]["files"] = [descriptor(record) for record in manifest["boundary_records"]]
            path.write_text(yaml.safe_dump(inputs, sort_keys=False, allow_unicode=True, width=120))
            from opportunity.acquire import lock_reviewed_inputs
            lock_reviewed_inputs(root)
        print(manifest["district_counts"])
    elif args.command == "inspect":
        from opportunity.acquire import inspect_file
        print(json.dumps(inspect_file(args.path), indent=2, default=str))
    elif args.command == "build":
        from opportunity.prepare import build
        try:
            build(root)
        except (ValueError, FileNotFoundError) as exc:
            raise SystemExit(f"Build blocked: {exc}") from exc
    elif args.command == "status":
        import yaml
        from opportunity.acquire import load_register
        records = load_register(root)
        config = yaml.safe_load((root / "config/verified_inputs.yml").read_text())
        for source_id in ("dft", "census", "imd", "ons"):
            attempts = [record for record in records if record["source_id"] == source_id]
            print(source_id + ": " + (attempts[-1]["status"] if attempts else "not attempted"))
        print(f'Reviewed input mappings: {bool(config.get("reviewed"))}')
        print(f'Processed data exists: {(root / "data/processed/neighbourhoods.parquet").exists()}')


if __name__ == "__main__":
    main()
