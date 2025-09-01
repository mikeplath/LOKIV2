#!/bin/bash

# Make sure the logs directory exists
mkdir -p /home/mike/LOKI/logs

# Check if the vector database exists
if [ ! -f "/home/mike/LOKI/vector_db/faiss_index.bin" ]; then
    echo "Error: Vector database not found."
    echo "Please run create_vector_db.sh first."
    exit 1
fi

# Get the query from the user
read -p "Enter a search query: " QUERY

# Run the test
echo "Searching for: $QUERY"
python3 /home/mike/LOKI/connect_vector_db.py --query "$QUERY" --k 10

echo ""
echo "Done. You can try another query by running this script again."
