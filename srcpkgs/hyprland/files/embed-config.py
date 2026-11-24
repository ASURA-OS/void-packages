#!/usr/bin/env python3
# Hyprland embeds its example config with #embed, which needs GCC 15; Void
# ships GCC 14. Write the same bytes as a comma-separated list to include.
import sys

src, dst = sys.argv[1], sys.argv[2]
with open(src, "rb") as f:
    data = f.read()
with open(dst, "w") as out:
    out.write(",".join(str(b) for b in data))
