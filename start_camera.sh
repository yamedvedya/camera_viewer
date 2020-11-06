BASEDIR=`dirname $0`
cd $BASEDIR

export VIEWERPATH=$PWD/
export PYTHONPATH=$PYTHONPATH:$VIEWERPATH
python ./src/main.py