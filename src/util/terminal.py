import struct
import fcntl
import termios


# set terminal winsize ioctl on file descriptor, used for our stdout/stderr
# streams so programs can query the dimensions for rendering graphical elements
# such as progress bars. this should match the rows & cols of frontend terminal
# https://stackoverflow.com/a/6420070
def set_winsize(fd, row, col, xpix=0, ypix=0):
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
