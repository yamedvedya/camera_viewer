BASEDIR=`dirname $0`
cd $BASEDIR

export VIEWERPATH=$PWD/
export PYTHONPATH=$PYTHONPATH:$VIEWERPATH
./venv/bin/python ./src/main.py