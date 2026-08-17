# Private implementation of the neopixel library: core and avr.
#
# A package rather than a set of _neopixel_*.py modules because the compiler's
# include path is flat and shared with every other installed library -- a bare
# core.py would be a global name. What the user imports is one level up.
