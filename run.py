# Download the twilio-python library from http://twilio.com/docs/libraries
import picamera
from twilio.rest import TwilioRestClient
from flask import Flask, request, redirect, session, render_template
import twilio.twiml
import serial
import sys
import time
import subprocess

class Photo(object):
    def __init__(self, question, epoch_time, big_file_path, small_file_path):
        self.big_path = big_file_path
        self.small_path = small_file_path
        self.question = question
        self.epoch_time = epoch_time #when picture taken
        pic_date = time.localtime(epoch_time)
        hr = pic_date.tm_hour
        tm_period = ""
        if (hr > 12): 
            hr = hr - 12
            tm_period = "PM"
        elif (hr == 0):
            hr = 12
            tm_period = "AM"
        elif (hr == 12):
            tm_period = "PM"
        else: 
            tm_period = "AM"

        date_str = "%d:%02d %s %d/%d/%d" % (hr, pic_date.tm_min, tm_period, pic_date.tm_mon,
                                            pic_date.tm_mday, pic_date.tm_year)

        self.title = "'%s' - %s" % (question, date_str)

ser = serial.Serial('/dev/ttyACM0', 115200)
using_ser = True

# The session object makes use of a secret key.
SECRET_KEY = 'a secret key'
app = Flask(__name__, static_url_path='', static_folder='')
app.config.from_object(__name__)


cur_idx = 100 #current question code
NUM_CODE_DIGITS = 3
QUESTION = 0
APPROVAL = 1

# question tuples are: (id, question, usr_num)
questions = []
photos = []
photo_pairs = []
max_photos = 5
is_odd = False
photo_count = 0

usr_num = ""
cur_question = "How are you today?"
question = "How are you today?"
ser.write((cur_question + "\n").encode('utf-8'))
mod_nums = ["+12018922065", "+14027409187"]
mod_nums = set(mod_nums)
twilio_num = "+14125150900"

# Find these values at https://twilio.com/user/account
account_sid = "AC9cd29475371662c58e19b738ea4f746f"
auth_token = "99ee049db9339bf4389891492e02b508"
client = TwilioRestClient(account_sid, auth_token)
 
@app.route("/sms/", methods=['GET', 'POST'])
def hello_monkey():
    """Respond and greet the caller by name."""
    global cur_idx
    global questions
    global cur_question

    is_question = True
    msg_body = request.values.get('Body', None)
    from_num = request.values.get('From', None)
    if ((from_num in mod_nums) and (msg_body[0:NUM_CODE_DIGITS]).isdigit()):
        is_question = False


    if (is_question):
        message = "Your question is being reviewed, and if approved will be added to the queue"
 
        resp = twilio.twiml.Response()
        resp.message(message)
        question = msg_body

        for num in mod_nums:
            mod_body = "New message to review: \n\n%s\n\nReply '%d yes' to approve and '%d no' to reject" % (msg_body, cur_idx, cur_idx)
            mod_message = client.messages.create(to=num, from_=twilio_num,
                                                 body=mod_body)

        usr_num = request.values.get('From', None)
        questions.append((cur_idx, msg_body, usr_num))

        cur_idx += 1
                                                 
        return str(resp)
    else:
        #moderator response
        msg_body = msg_body.lower();

        idx = int(msg_body[0:NUM_CODE_DIGITS])
        resp_str = (msg_body[NUM_CODE_DIGITS:]).strip()
        is_approved = False
        is_valid = True

        quest_tuple = (-1, "", "")
        #find question in list
        for i in range(len(questions)):
            if((questions[i])[0] == idx):
                quest_tuple = questions.pop(i)
                break

        if (quest_tuple[0] == -1):
            is_valid = False
        else:
            if(resp_str == "yes"):
                #respond to user
                is_approved = True
                usr_message = client.messages.create(to=quest_tuple[2], from_=twilio_num,
                                                 body="Your message was approved")

                cur_question = quest_tuple[1]
                #write to display
                output = quest_tuple[1] + '\n'
                if(using_ser):
                    output_bytes = output.encode('utf-8')
                    ser.write(output_bytes);
                print ("new question: %s" % output)
            else:
                usr_message = client.messages.create(to=quest_tuple[2], from_=twilio_num,
                                                 body="Your message was rejected")


        #formulate response to mod
        resp = twilio.twiml.Response()
        if(not is_valid):
            resp.message("That was not a valid response")
        elif(is_approved):
            resp.message("You just approved message %d" % idx)
        else:
            resp.message("You just rejected message %d" % idx)

        return str(resp)
 

@app.route("/pictures/")
def website():
    '''
    secs = time.time()
    photo1 = Photo("how are you?", secs, "board-big.jpg", "board.jpg")
    photo2 = Photo("What are you brining to the potluck?", secs + 120, "board-big.jpg", "board.jpg")
    photo3 = Photo("best part of Greenville?", secs + 360, "board-big.jpg", "board.jpg")
    print secs
    print "\n"

    test = [(photo1, photo2), (photo3, photo3)]
    '''
    #subprocess.call(['./get_pic.sh', 'current.jpg'])
    #subprocess.call(['convert', 'current.jpg', '-resize', '20%', 'current_small.jpg'])
    if (len(photos) > 0):
        last = len(photos) - 1
        return render_template("home.html", 
                               current_img_path_sml=photos[last].small_path, 
                               current_img_path_big=photos[last].big_path, 
                               photos=photo_pairs, 
                               is_odd=is_odd, 
                               current_question=photos[last].question)
    else:
        return ""


@app.route("/take_photo/")
def take_pic():
    global photos
    global photo_pairs
    global is_odd
    global photo_count

    pic_prefix = "%s%s" % ('pic', str(photo_count))
    pic_name = "%s.jpg" % pic_prefix
    small_pic_name = "%s-small.jpg" % pic_prefix

    photo_count += 1
    print "taking photo named: %s" % pic_name

    #camera.capture(pic_name);

    subprocess.call(['/home/pi/physComp/twilio/get_pic.sh', pic_name])
    print 'resizing image to be named %s' % small_pic_name

    subprocess.call(['convert', pic_name, '-resize', '20%', small_pic_name])

    photos.append(Photo(cur_question, int(time.time()), pic_name, small_pic_name))
    if (len(photos) > max_photos):
        del photos[0] #delete oldest photo

    #create new photo_pairs list
    is_odd = True if ((len(photos) - 1) % 2) == 1 else False
    photo_pairs = []
    for i in range(len(photos)-2, -1, -2):
        if(i - 1 >= 0):
            photo_pairs.append((photos[i], photos[i-1]))
        else:
            photo_pairs.append((photos[i], Photo("", 0, "", "")))

    return ""

if __name__ == "__main__":
    
    app.run(debug=True)
