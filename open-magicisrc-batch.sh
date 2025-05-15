#!/bin/bash
while read -u 3 -r logfile; do
    echo $logfile
    python3 open-magicisrc.py "$logfile"
done 3< <(find ~/Desktop/xld-out -path ~/Desktop/xld-out/\!done/zipdisc -prune -o -type f -name "*.log")

echo -e "\n\n\nAll done!"