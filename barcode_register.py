#### Camera dependencies

from imutils.video import VideoStream
from pyzbar import pyzbar
import argparse
import datetime
import imutils
import time
import cv2

#### Position dependencies
from marvelmind import MarvelmindHedge
from time import sleep
import sys

#### API dependencies
import requests
import json

#### Camera init:
ap = argparse.ArgumentParser()
ap.add_argument("-o", "--output", type=str, default="barcodes.csv",
	help="path to output CSV file containing barcodes")
args = vars(ap.parse_args())

# initialize the video stream and allow the camera sensor to warm up
print("[INFO] starting video stream...")
# vs = VideoStream(src=0).start()
vs = VideoStream(usePiCamera=True).start()
time.sleep(2.0)

# open the output CSV file for writing and initialize the set of
# barcodes found thus far
csv = open(args["output"], "w")
found = set()

### Position MarvelMind init

hedge = MarvelmindHedge(tty = "/dev/ttyACM0", adr=None, debug=False) # create MarvelmindHedge thread
if (len(sys.argv)>1):
    hedge.tty= sys.argv[1]

hedge.start() # start thread

### Functions

def read_position():
    try:
        hedge.dataEvent.wait(1)
        hedge.dataEvent.clear()

        if (hedge.positionUpdated):
            position = hedge.position()
    except KeyboardInterrupt:
        hedge.stop()
        sys.exit()
    return position

def send_2_api(barcodeData,position):
    barcode_separated = barcode_parser(barcodeData)
    warehouse_position = position_parser(position)

    post_headers = {'Content-type': 'application/json'}
    load_json = {
    "Dispositivo": "Raspberry1-Real",
    "codigo": barcode_separated,
    "Ubicacion": warehouse_position,
    "temperatura":"20"
    }
    jsonData = json.dumps(load_json)
    postresponse = requests.post(url_logistica,
                         data=jsonData,
                         headers=post_headers)
    print("Status code of POST: ", postresponse.status_code)
    return postresponse.status_code

def barcode_parser(barcodeData):
    pass

def position_parser(position):
    pass

# loop over the frames from the video stream
while True:

    # Read position
    position = read_position()

	# grab the frame from the threaded video stream and resize it to
	# have a maximum width of 400 pixels
	frame = vs.read()
	frame = imutils.resize(frame, width=400)

	# find the barcodes in the frame and decode each of the barcodes
	barcodes = pyzbar.decode(frame)

	# loop over the detected barcodes
	for barcode in barcodes:
		# extract the bounding box location of the barcode and draw
		# the bounding box surrounding the barcode on the image
		(x, y, w, h) = barcode.rect
		cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

		# the barcode data is a bytes object so if we want to draw it
		# on our output image we need to convert it to a string first
		barcodeData = barcode.data.decode("utf-8")
		barcodeType = barcode.type

		# draw the barcode data and barcode type on the image
		text = "{} ({})".format(barcodeData, barcodeType)
		cv2.putText(frame, text, (x, y - 10),
		cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

		# if the barcode text is currently not in our CSV file, write
		# the timestamp + barcode to disk and update the set
		if barcodeData not in found:
            id_db = send_2_api(barcodeData, position)
			csv.write("{},{}, X: {}, Y: {}, Z: {}, id: {}\n".format(datetime.datetime.now(),
				barcodeData, str(position[0]), str(position[1]), str(position[2]), id_db))
			csv.flush()
			found.add(barcodeData)

            send_2_api(barcodeData, position)

	# show the output frame
	cv2.imshow("Barcode Scanner", frame)
	key = cv2.waitKey(1) & 0xFF

	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break

# close the output CSV file do a bit of cleanup
print("[INFO] cleaning up...")
csv.close()
cv2.destroyAllWindows()
vs.stop()
# Close marvelmindModule
hedge.stop()
sys.exit()