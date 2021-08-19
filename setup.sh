# Created by matveyev at 07.04.2021

BASEDIR=`dirname $0`
cd $BASEDIR || exit

export VIEWERPATH=$PWD/
export PYTHONPATH=$PYTHONPATH:$VIEWERPATH

python3 .setup/build.py
python3 .setup/make_alias.py
chmod +x start_camera.sh

cp ./sample_config.xml ./config.xml

{
  python3 -m venv --system-site-packages ./venv
} || {
pip install --user virtualenv
$HOME/.local/bin/virtualenv  -p python3 --system-site-packages venv
}
. venv/bin/activate

pip3 install watchdog
pip3 install scikit-image