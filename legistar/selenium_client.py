'''Creates a firefox browser instance that runs in a
virtual display. Importantly, shuts it down when the
script ends, so tons of invisible, zombie firefoxes don't
eat all the system memory.
'''
import atexit

from pyvirtualdisplay import Display
from selenium import webdriver


display = Display(visible=0, size=(800, 600))
display.start()
browser = webdriver.Firefox()

def shutdown():
    browser.quit()
    display.stop()

atexit.register(shutdown)