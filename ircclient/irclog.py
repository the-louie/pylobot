import logging

class IRCHandler(logging.Handler): # Inherit from logging.Handler
        def __init__(self, sendfunc):
                # run the regular Handler __init__
                logging.Handler.__init__(self)
                # Our custom argument
                self.sendfunc = sendfunc

        def emit(self, record):
                # record.message is the log message
                if (self.sendfunc):
                	self.sendfunc(record.message)