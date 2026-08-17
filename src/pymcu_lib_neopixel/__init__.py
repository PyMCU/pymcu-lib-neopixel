"""
WS2812/NeoPixel LED strips for PyMCU.

Nothing here runs under CPython. The modules the compiler reads are package
data under mcu/, and PyMCU puts that directory -- and only that directory --
on the include path when a project depends on this distribution. From a
firmware it is a top-level import:

    from neopixel import NeoPixel
"""
