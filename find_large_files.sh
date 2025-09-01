#!/bin/bash

echo "Looking for files larger than 50MB..."
find . -type f -size +50M | sort -h

echo -e "\nLooking for files larger than 10MB..."
find . -type f -size +10M | sort -h
