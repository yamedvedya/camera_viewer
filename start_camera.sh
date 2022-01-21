BASEDIR=`dirname $0`
cd $BASEDIR

export VIEWERPATH=$PWD/
export PYTHONPATH=$PYTHONPATH:$VIEWERPATH
./venv/bin/python ./petra_camera.py