#!/bin/bash

git add .
git commit -m "Update - $timedate"
git branch --set-upstream-to=origin/dev dev
git push
git branch --unset-upstream