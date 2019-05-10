import datetime
import os
import re
import sys
from subprocess import call
from tempfile import NamedTemporaryFile
from time import sleep

from gtts import gTTS
from pynput import mouse, keyboard


class SirBugMeLot:
    buglevels = {
        'Low': 5 * 60,
        'Med': 2 * 60,
        'High': 30,
    }

    def __init__(self):
        self.first_press = self.last_press = self.last_pause = self.last_bug = self.last_log = self.now()
        self.base_path = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.logfile = open(os.path.join(self.base_path, 'bugme.log'), "w")
        self.config = self.read_config()
        self.workspan = 0
        self.buglvl = 5
        self.bugsound = self.config['sound_lvl1']
        self.playing = False

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
    def play_mp3(file_path: str):
        if file_path is None or not os.path.isfile(file_path):
            return
        fnull = open(os.devnull, 'w')
        call(["ffplay", "-autoexit", "-nodisp", str(file_path)], stdout=fnull, stderr=fnull, close_fds=True)

    def check_bugme(self):
        self.workspan = self.last_press - self.first_press
        if self.playing or self.workspan < 60:
            return
        if self.set_buglevel():
            # buglevel changed, bug him
            self.bug_him()
        # Check if pause was done
        if self.last_press - self.last_pause > self.config['pausetime']:
            self.first_press = self.now()
            self.last_bug = self.now()
            paused_minutes = str(round((self.last_press - self.last_pause) / 60))
            self.playing = True
            if self.config['use_tts']:
                self.speak('You just had a {} minute pause'.format(paused_minutes))
            else:
                self.play_mp3(self.config['sound_pause'])
            self.write_log('Pause of {} minutes registered, resetting timer'.format(paused_minutes))
            self.playing = False
            return
        # Check if bugging is necessary
        seconds_since_bug = self.now() - self.last_bug
        if self.workspan > self.config['worktime_max'] and seconds_since_bug > self.buglvl:
            self.bug_him()
        elif self.last_press - self.last_pause > 60 or self.now() - self.last_log > 120:
            self.write_log('Working for {} minutes'.format(round(self.workspan / 60, 2)))
            self.last_log = self.now()
        self.last_pause = self.last_press

    def speak(self, msg):
        tts = gTTS(text=msg, lang='en')
        f = NamedTemporaryFile()
        tts.write_to_fp(f)
        f.flush()
        self.play_mp3(f.name)
        f.close()

    def bug_him(self):
        if self.playing:
            return
        self.playing = True
        if self.config['use_tts']:
            work_minutes = str(round(self.workspan / 60))
            if self.buglvl == self.buglevels['Low']:
                bug_msg = 'You have been working for {} minutes, you should take a break.'.format(work_minutes)
            elif self.buglvl == self.buglevels['Med']:
                bug_msg = 'You are working {} minutes now, take a break.'.format(work_minutes)
            else:
                bug_msg = 'It has been {} minutes now, get moving.'.format(work_minutes)
                self.play_mp3(self.bugsound)
            self.speak(bug_msg)
        else:
            self.play_mp3(self.bugsound)
        self.last_bug = self.now()
        self.write_log('Bugging after {} minutes'.format(round(self.workspan / 60, 2)))
        self.playing = False

    def set_buglevel(self):
        # Adjust bug level according to uninterrupted working time
        if self.workspan >= self.config['worktime_max'] + 20 * 60:
            if self.buglvl != self.buglevels['High']:
                self.buglvl = self.buglevels['High']
                self.bugsound = self.config['sound_lvl3']
                self.write_log('Setting buglevel to High at workspan {} minutes'.format(round(self.workspan / 60)))
                return True
        elif self.workspan >= self.config['worktime_max'] + 10 * 60:
            if self.buglvl != self.buglevels['Med']:
                self.buglvl = self.buglevels['Med']
                self.bugsound = self.config['sound_lvl2']
                self.write_log('Setting buglevel to Med at workspan {} minutes'.format(round(self.workspan / 60)))
                return True
        elif self.workspan >= self.config['worktime_max']:
            if self.buglvl != self.buglevels['Low']:
                self.buglvl = self.buglevels['Low']
                self.bugsound = self.config['sound_lvl1']
                self.write_log('Setting buglevel to Low at workspan {} minutes'.format(round(self.workspan / 60)))
                return True
        return False

    def read_config(self):
        result = {}
        default_sound_path = os.path.join(self.base_path, 'bugme.mp3')
        if not os.path.isfile(default_sound_path):
            raise FileNotFoundError(default_sound_path)
        # sane defaults
        defaults = {
            'worktime_max': 45,
            'pausetime': 5,
            'sound_lvl1': 'lvl1.mp3',
            'sound_lvl2': 'lvl2.mp3',
            'sound_lvl3': 'lvl3.mp3',
            'sound_pause': 'pause.mp3',
            'use_tts': False,
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
            if k == 'use_tts':
                result[k] = bool(v)
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
    sys.stdout.write('Missing file: ' + str(e.args[0]))
