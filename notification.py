import os
import subprocess
from warnings import warn


# Visible notifications
try:
    import pynotify
except ImportError:
    warn('Visible alerts are disabled')
    pynotify = None
else:
    pynotify.init('timetracker')


# Audible notifications
try:
#    sys.path.insert(0, '/home/andy/src')
#    import beeper   # custom script, see http://paste.pocoo.org/show/316/
#    import beeper_alsa
    subprocess.Popen(['beep', '-l', '0'])
except OSError:
    warn('Simple audible alerts are disabled')
    beep_enabled = False
else:
    beep_enabled = True


__all__ = ['beep', 'say', 'show']


def beep(*pairs):
    """Emits beeps using the "beep" program."""
    if not beep_enabled:
        return
    beeps = []
    for frequency, duration in pairs:
        beeps.extend(['-f', str(frequency), '-l', str(duration), '-n'])
    beeps.pop()   # remove the last "-n" separator to prevent extra beep
    subprocess.Popen(['beep'] + beeps) #, '-f', str(frequency), '-l', str(duration)])
    #'beep -f 100 -n -f 150 -n -f 50 -n -f 300 -n -f 200 -n -f 400'.split())
#    try:
#        beeper.beep(frequency, duration)
#    except IOError:
#        beeper_alsa.beep(frequency, duration)


def say(text):
    """Uses Festival TTS to actually say the message."""
    # see http://ubuntuforums.org/showthread.php?t=751169
    sound_wrapper = 'padsp'  # or 'aoss' or 'esddsp' or none
    command = 'echo \'(SayText "{text}")\' | {sound_wrapper} festival &'
    text = text.replace('"','').replace("'",'')
    os.system(command.format(sound_wrapper=sound_wrapper, text=text))


def show(text, critical=False):
    if not pynotify:
        return False

    note = pynotify.Notification(summary=text)
    if critical:
        note.set_urgency(pynotify.URGENCY_CRITICAL)
    note.show()
    return True