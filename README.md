# About
Sir BugMeLot is a little helper to bug you if you stay in front of the computer for too long.

It listens to mouse- and keyboard- events and runs an internal timer to measure the time you are active. It detects pauses and resets the timer if a pause is finished. If you exceed the configured time it will start to bug you, getting more annoying until you pause.

# Install
1. Clone the repo and create Python3 virtualenv
2. Install ffmpeg ("sudo apt-get install ffmpeg" for debian/ubuntu/mint)
3. Activate venv and do "pip install -r requirements.txt"

# Usage
1. Copy .env.dist to .env and adjust if needed (optional)
2. Copy custom mp3 files into dir (optional)
3. Use provided run.sh or run with
```bash
nohup python sirbugmelot.py > /dev/null &
```

SirBugMeLot will run in the background and start bugging you after the configured time. It intentionally does not have a kill switch. You will have to use ps and kill to manually kill the process.

# License
MIT License. Do whatever you want with it.

# Attribution
Sounds are from [orangefreesounds](http://www.orangefreesounds.com/) and licensed under [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/)
