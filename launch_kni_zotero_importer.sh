#!/bin/zsh

cd /Users/anup/gitProjects/zotero-import || exit 1

mkdir -p /Users/anup/gitProjects/zotero-import/logs
nohup /Library/Frameworks/Python.framework/Versions/3.10/bin/python3 \
  /Users/anup/gitProjects/zotero-import/run_kni_zotero_importer.py \
  >/Users/anup/gitProjects/zotero-import/logs/gui_launcher.log 2>&1 </dev/null &
