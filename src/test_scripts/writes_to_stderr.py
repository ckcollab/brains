import sys
import time

for _ in range(50):
	print "Also writes to stdout"
	sys.stderr.write("Oh my GOD an error!\n")
	time.sleep(0.25)

