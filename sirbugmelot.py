import datetime
import os
import re
import sys
from subprocess import call
from time import sleep

from pynput import mouse, keyboard


class SirBugMeLot:
    buglevels = {
        'Low': 5 * 60,
        'Med': 2 * 60,
        'High': 30,
    }

    def __init__(self):
        self.base_path = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.logfile = open(os.path.join(self.base_path, 'bugme.log'), "w")
        self.last_log = self.now()
        self.workspan = 0
        self.first_press = self.last_press = self.last_pause = self.last_bug = self.now()
        self.buglvl = 5 * 60
        self.config = self.read_config()

    def write_log(self, msg):
        self.logfile.write(msg + "\n")
        self.logfile.flush()

    @staticmethod
    def now():
        return datetime.datetime.utcnow().timestamp()

    # noinspection PyUnusedLocal
    def mouse_count(self, x, y):
        self.last_press = self.now()
        self.check_bugme()

    # noinspection PyUnusedLocal
    def key_count(self, key):
        self.last_press = self.now()
        self.check_bugme()

    @staticmethod
    def play_mp3(file: str):
        if file is None or not os.path.isfile(file):
            return
        call(["ffplay", "-nodisp -autoexit {} > /dev/null 2>&1".format(file)])

    def check_bugme(self):
        self.workspan = self.last_press - self.first_press
        # Adjust bug level according to uninterrupted working time
        if self.workspan >= self.config['worktime_max'] + 20 * 60:
            self.buglvl = self.buglevels['High']
            self.write_log('Setting buglevel to High at workspan {} minutes'.format(round(self.workspan / 60)))
        elif self.workspan >= self.config['worktime_max'] + 10 * 60:
            self.buglvl = self.buglevels['Med']
            self.write_log('Setting buglevel to Med at workspan {} minutes'.format(round(self.workspan / 60)))
        elif self.workspan >= self.config['worktime_max']:
            self.buglvl = self.buglevels['Low']
            self.write_log('Setting buglevel to Low at workspan {} minutes'.format(round(self.workspan / 60)))
        # Check if pause was done
        if self.last_press - self.last_pause > self.config['pausetime'] * 60:
            self.first_press = self.now()
            self.write_log('Pause of {} minutes registered, resetting timer'
                           .format(round((self.last_press - self.last_pause) / 60)))
        # Check if bugging is necessary
        seconds_since_bug = self.now() - self.last_bug
        if self.workspan > self.config['worktime_max'] and seconds_since_bug > self.buglvl:
            self.last_bug = self.now()
            self.play_mp3(self.config['sound_lvl1'])
            self.write_log('Bugging after {} minutes'.format(round(self.workspan / 60, 2)))
        elif self.last_press - self.last_pause > 60 or self.now() - self.last_log > 120:
            self.write_log('Working for {} minutes'.format(round(self.workspan / 60, 2)))
            self.last_log = self.now()
        self.last_pause = self.last_press

    def read_config(self):
        result = {}
        default_sound_path = os.path.join(self.base_path, 'bugme.mp3')
        if not os.path.isfile(default_sound_path):
            raise FileNotFoundError(default_sound_path)
        # sane defaults
        defaults = {
            'worktime_max': 45 * 60,
            'pausetime': 5 * 60,
            'sound_lvl1': 'bugme.mp3',
            'sound_lvl2': 'bugme.mp3',
            'sound_lvl3': 'bugme.mp3',
            'sound_pause': 'pause.mp3',
        }
        # read from .env
        env_path = os.path.join(self.base_path, '.env')
        if os.path.isfile(env_path):
            envre = re.compile(r'''^([^\s=]+)=(?:[\s"']*)(.+?)(?:[\s"']*)$''')
            with open(env_path) as env_file:
                for line in env_file:
                    match = envre.match(line)
                    if match is not None:
                        result[match.group(1)] = match.group(2)
        # Verify config
        for k, v in defaults.items():
            if k not in result:
                result[k] = v
        for k, v in result.items():
            if k == 'worktime_max':
                result[k] = int(v) * 60 if int(v) > 0 else 45 * 60
            if k == 'pausetime':
                result[k] = int(v) * 60 if int(v) > 0 else 5 * 60
            if k in ('sound_lvl1', 'sound_lvl2', 'sound_lvl3', 'sound_pause'):
                sound_file_path = os.path.join(self.base_path, v) if re.match('.*mp3$', v) else default_sound_path
                result[k] = sound_file_path if os.path.isfile(sound_file_path) else default_sound_path
            if k == 'sound_pause':
                sound_file_path = os.path.join(self.base_path, v) if re.match('.*mp3$', v) else None
                result[k] = sound_file_path if os.path.isfile(sound_file_path) else None
        self.write_log('Config read: ' + result.__str__())
        return result


try:
    sbml = SirBugMeLot()
    mlistener = mouse.Listener(on_move=sbml.mouse_count)
    mlistener.start()
    klistener = keyboard.Listener(on_press=sbml.key_count)
    klistener.start()
    while True:
        sleep(5)
except FileNotFoundError as e:
    sys.stdout.write('Missing file: ' + e.args[0])
