#!/usr/bin/env python2
'''
This utility transcodes any input video file using mplayer and x264,
encoding it at 0.06 bits per pixel. The result is then muxed by mkvmerge
(audio is just copied from the original).

Thanks to x264, the result is an optimal balance between size and quality.
'''

import os
import sys
import getopt
from misc import panic


def usage():
    print '''
Usage: {prog} <options>

where options are:

    -h, --help                     This help message
    -i, --input <inputVideoFile>   The file to read from
    -o, --output <outputVideoFile> The output .mkv file to create
'''.format(prog=os.path.basename(sys.argv[0]))
    sys.exit(1)


def computeRate(inputVideo):
    keys = [
        'ID_VIDEO_WIDTH',
        'ID_VIDEO_HEIGHT',
        'ID_VIDEO_FPS']
    values = {}
    for line in os.popen(
            "mplayer -identify -frames 0 -vo null \"%s\" 2>/dev/null" %
            inputVideo).readlines():
        for key in keys:
            if line.startswith(key):
                try:
                    values[key] = float(line.strip().split('=')[1])
                except:
                    panic("Failed to parse %s..." % line.strip())
                break
    for key in keys:
        if key not in values.keys():
            panic("Failed to find %s for %s" % (key, inputVideo))
    return int(0.06 * reduce(lambda x, y: x * y, values.values()) / 1000.0)


def main():
    try:
        args = sys.argv[1:]
        optlist, args = getopt.gnu_getopt(
            args, "hi:o:", ['help', 'input', 'output'])
    except:
        usage()

    if args:
        usage()

    inputVideo = None
    outputVideo = None
    for opt, arg in optlist:
        if opt in ("-h", "--help"):
            usage()
        elif opt in ("-i", "--input"):
            inputVideo = arg
        elif opt in ("-o", "--output"):
            outputVideo = arg
        else:
            usage()

    if not inputVideo or not outputVideo:
        usage()

    inputVideo = os.path.abspath(inputVideo).replace("'", "'\"'\"'")
    outputVideo = os.path.abspath(outputVideo).replace("'", "'\"'\"'")
    outputRate = computeRate(inputVideo)
    pid = str(os.getpid())
    os.system("rm -f x264*log* /tmp/fifo" + pid)
    os.system("mkfifo /tmp/fifo" + pid)
    cmdPlay = "mplayer -nosound -benchmark -vo yuv4mpeg:file=/tmp/fifo" + pid
    cmdPlay += " '" + inputVideo + "' &"
    cmdEncodeCommon = "x264 --demuxer y4m --threads auto --pass %d --bitrate "
    cmdEncodeCommon += str(outputRate)
    cmdPass1 = cmdEncodeCommon % 1 + " -o /dev/null " + \
        "/tmp/fifo" + pid + " 2>x264.1.log"
    cmdPass2 = cmdEncodeCommon % 2 + " -o '" + outputVideo + ".video' " + \
        "/tmp/fifo" + pid + " 2>x264.2.log"

    # Video, pass 1
    os.system(cmdPlay)
    os.system(cmdPass1)

    # Video, pass 2
    os.system(cmdPlay)
    os.system(cmdPass2)

    # Audio, merge from original
    os.system(
        "mkvmerge -o '" + outputVideo + "' " +
        "-A '" + outputVideo + ".video' " +
        "-D '" + inputVideo + "'")
    os.system("rm '" + outputVideo + ".video' /tmp/fifo" + pid)


if __name__ == "__main__":
    main()
