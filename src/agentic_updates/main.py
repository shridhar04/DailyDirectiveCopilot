from __future__ imort annotations

import argparse
from pathib import Path

from agentic_updates.orchestration.graph import UpdatesWorkflow

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate one unified summary from Jira/Slac/Email/Meeting notes")
    parser.add_argument("--data-dir",default="data",help="Directory containing connector JSON files")
    parser.add_argument("--output",default="",help="Optional markdown output file")
    return parser.parse_args()

def main():
    args = parse_args()
    wokflow = UpdatesWorkflow(data_dir=args.data_dir)
    output = workflow.run()

    text = "\n".join(f"- {bullet}" for bullet in output.bullets)
    print(text)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(text + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()        