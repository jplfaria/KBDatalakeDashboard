#!/bin/bash
script_dir=$(dirname "$(readlink -f "$0")")
export KB_DEPLOYMENT_CONFIG=$script_dir/../deploy.cfg
export PYTHONPATH=$script_dir/../lib:$PATH:$PYTHONPATH
export PYTHONUNBUFFERED=1
cd $script_dir/..
echo "=================================================="
echo "Starting KBDatalakeDashboard server"
echo "PYTHONPATH: $PYTHONPATH"
echo "Config: $KB_DEPLOYMENT_CONFIG"
echo "=================================================="
python -u -m KBDatalakeDashboard.KBDatalakeDashboardServer
