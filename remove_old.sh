#!/bin/bash

echo "Cleaning old build files..."
rm -rf *.egg-info > /dev/null 2>&1
rm -rf build > /dev/null 2>&1
rm -rf dist > /dev/null 2>&1
echo "Done"
