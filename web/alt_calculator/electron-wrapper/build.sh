#!/bin/bash

# Build React app
cd ../client
npm run build

# Return to electron wrapper and build executable
cd ../electron-wrapper
npm run dist