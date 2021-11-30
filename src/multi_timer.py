#
# Multi-Timer display. Based on the Alexa Gadget Timer example.
#
# Can handle as many timers as there are slots in the timerlist table
#
# Display is handled through background thread. Should really use locks to access table.....
#

import logging
import sys
import threading
import time

import fourletterphat

import dateutil.parser

from agt import AlexaGadget

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

class TimerGadget(AlexaGadget):
    """
    An Alexa Gadget that reacts to multiple timers set on an Echo device.

    Uses a PHAT display for the time.  

    Threading is used to prevent blocking the main thread when the timer is
    counting down.
    """

    # Add more here for more timers.
    timerlist = [{'token':0, 'timeout':0} for i in range(8)]

    def __init__(self):
        super().__init__()
        self.timer_thread = None
        self.max_timer = 0;

        print("We are in Init")

        fourletterphat.clear()
        fourletterphat.print_str("WAIT")
        fourletterphat.show()

        time.sleep(1)


    def list_timers(self):
        i=1
        for tmr in self.timerlist:
            print("{} - Token:{}, Timeout:{}".format(i, tmr['token'], tmr['timeout']))
            i = i + 1


    def add_timeout(self, token, timeout):

        logger.info("Adding timeout:{} for token:{}".format(timeout, token))

        if (timeout > self.max_timer):
            self.max_timer = timeout+1

        slot_found = False
        for tmr in self.timerlist:
            if (tmr['token'] == 0 or tmr['token'] == token):
                tmr['token'] = token
                tmr['timeout'] = timeout
                slot_found = True
                break;

        if(slot_found):
            pass
        else:
            logger.info("No room to add token")

    def del_timeout(self, token):
        logger.info("Deleting token:{}".format(token))

        slot_found = False
        for tmr in self.timerlist:
            if (tmr['token'] == token):
                tmr['token'] = 0;
                tmr['timeout'] = 0
                slot_found = True

        if(slot_found):
            pass
        else:
            logger.info("Did not find token")


    def find_shortest_timer(self):

        # print("Looking for timer with lowest value")

        min_token = 0;
        min_timer = self.max_timer
        for tmr in self.timerlist:
            if (tmr['token'] != 0):
                if(tmr['timeout'] < min_timer):
                    min_timer = tmr['timeout']
                    min_token = tmr['token']

        if (min_token == 0):
            return 0,0
        else:
            return min_token, min_timer


    def on_connected(self, device_address):
        print("We are connected")

        fourletterphat.clear()
        fourletterphat.print_str("HELO")
        fourletterphat.show()

        time.sleep(2)

        fourletterphat.clear()
        fourletterphat.show()


    def on_alerts_setalert(self, directive):
        """
        Handles Alerts.SetAlert directive sent from Echo Device
        """

        # check that this is a timer. if it is something else (alarm, reminder), just ignore
        if directive.payload.type != 'TIMER':
            logger.info("Received SetAlert directive but type != TIMER. Ignorning")
            return

        # parse the scheduledTime in the directive. if is already expired, ignore
        t = int(dateutil.parser.parse(directive.payload.scheduledTime).timestamp())
        if t <= 0:
            logger.info("Received SetAlert directive but scheduledTime has already passed. Ignoring")
            return

        # Add this timer or update it if its already exists
        logger.info("Received SetAlert directive adding/updating entry to table.")
        self.add_timeout(directive.payload.token, t)

        # Run the main loop as a thread. Start if not running
        if (self.timer_thread == None):
            self.timer_thread = threading.Thread(target=self.main_timer_thread)
            self.timer_thread.start()

    def on_alerts_deletealert(self, directive):
        """
        Handles Alerts.DeleteAlert directive sent from Echo Device
        """
        # Remove the entry from the table
        logger.info("Received DeleteAlert directive. Remove the timer")
        self.del_timeout(directive.payload.token)


    #
    # Main loop (thread) to manage the display of the timers
    #
    def main_timer_thread(self):

        # spinner = ["|", "/", "-", "\\"]
        spinner = ["|/-\\", "/-\\|", "-\\|/", "\\|/-"]

        logger.info("Starting up timer thread")
        while True:
            token,timeout = self.find_shortest_timer()
    
            if (token == 0):
                # Nothing found, so exit this thread
                print("No timers running, nothing left to do")
                break
    
            time_remaining = int(timeout - time.time())
            if (time_remaining > 0):
                # Timer still running, display it
                # then sleep for 0.5 seconds
                print("Token:{} has {} seconds remaining".format(token, time_remaining))
                curr_minutes = int(time_remaining / 60.0)
                curr_seconds = int(time_remaining % 60)
                padded_str = str("{0:02d}".format(curr_minutes)) + str("{0:02d}".format(curr_seconds))

                fourletterphat.clear()
                fourletterphat.print_str(padded_str)
                fourletterphat.set_decimal(1, 1)
                fourletterphat.show()

                time.sleep(0.5)
    
            elif (time_remaining < -10):
                # Timer has long expired, just remove it and go back around
                print("Token:{} has long expired, removing it".format(token))
                self.del_timeout(token)
    
            else:
                # Timer has just expired (within 10sec) so show spinners
                print("Token:{} has expired".format(token))
                for i in range(4):
                    for s in spinner:
                        #s = s * 4
                        fourletterphat.clear()
                        fourletterphat.print_str(s)
                        fourletterphat.show()
                        time.sleep(1 / 16.0)


        fourletterphat.clear()
        fourletterphat.show()
        logger.info("Stopping timer thread")
        self.timer_thread = None


if __name__ == '__main__':
    try:
        TimerGadget().main()
    finally:
        logger.debug('All done')
