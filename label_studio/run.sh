#!/bin/bash
export BASEPATH="."
export LABEL_STUDIO_PORT=8787
export LABEL_STUDIO_BASE_DATA_DIR="$BASEPATH/data"

source $BASEPATH/env/bin/activate

label-studio start \
	--no-browser \
	--port $LABEL_STUDIO_PORT \
    --data-dir $LABEL_STUDIO_BASE_DATA_DIR
