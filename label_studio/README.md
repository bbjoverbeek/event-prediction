# openboek_labelstudio

## Installing Label Studio and starting the local server

See <https://labelstud.io/guide/install.html> for more info

Run the following commands:

```bash
python3 -m venv env  # create virtual environment
source env/bin/activate  # activate virtual environment
python3 -m pip install -r requirements.txt  # install label studio
bash run.sh # start label studio
```

Label studio will now start running at <http://localhost:8787>

To stop running Label Studio, press Ctrl+c

To add the events project to your label studio instance, run `python3 setup.py` in another terminal.

Note: for this to work, add your personal API key to the config.py file. The key can be found under Account & Settings.


The pre-annotations were created using the scripts in the formatting_scripts folder.
