#!/bin/bash

branch = "dev"

if [ -n "$1" ]; then
    branch = $1
fi

git add .
git commit -m "Update - $timedate"
git branch --set-upstream-to=origin/$branch $branch
git push
git branch --unset-upstream