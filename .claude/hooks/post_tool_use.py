#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import sys

def main():
    print("post_tool_use hook called")
    sys.exit(0)

if __name__ == '__main__':
    main()