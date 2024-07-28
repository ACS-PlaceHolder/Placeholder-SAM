#!/bin/bash

set -e

# Create a build directory
mkdir -p build/python

# Install dependencies into the build directory
pip install -r requirements.txt -t build/python

# Zip the dependencies
cd build
zip -r9 ../dependencies.zip .
cd ..

# Cleanup
rm -rf build
