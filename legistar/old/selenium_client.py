'''Creates a firefox browser instance that runs in a
virtual display. Importantly, `shutdown` shuts it down
when the script ends.
'''
import atexit

from pyvirtualdisplay import Display
from selenium import webdriver


display = Display(visible=0, size=(800, 600))
display.start()
browser = webdriver.Firefox()
browser.implicitly_wait(10)


def shutdown():
    '''This callback shuts down the drowser and terminates
    the virtual display so they don't continue to exists
    after the program finishes.
    '''
    browser.quit()
    try:
        display.stop()
    except NameError:
        pass

atexit.register(shutdown)