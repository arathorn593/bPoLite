#!/bin/bash

source /home/pi/physComp/twilio/bin/activate
python /home/pi/physComp/twilio/run.py &> /home/pi/physComp/twilio/run_log.txt &
/home/pi/physComp/twilio/ngrok http -subdomain=bpolite 5000
