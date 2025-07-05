#!/bin/bash

# Create directories if they don't exist
mkdir -p static/images

# Run the application in the background
nohup python app.py > server.log 2>&1 &

echo "Server started! Access it at https://work-1-plcvfzwuzodkriqz.prod-runtime.all-hands.dev"
echo "To stop the server, run: pkill -f 'python app.py'"