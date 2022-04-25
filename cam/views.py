from datetime import datetime
import PIL
from django.utils import timezone
import os
import threading
import cv2
from django.http.response import StreamingHttpResponse
from django.shortcuts import render
import numpy as np
from cam.models import Image
from PIL import Image

from member.models import User

directory= os.getcwd()
filePath = directory + '/capture/'
paths=directory+'/dataset/'
trainpath=directory+'/trainer/trainer.yml'
recognizer = cv2.face.LBPHFaceRecognizer_create()
detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def cap(request):
	cam = cv2.VideoCapture(0,cv2.CAP_DSHOW)
	cam.set(3, 640) # set video width
	cam.set(4, 480) # set video height
	face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
	path=directory+"/dataset/User."
	# For each person, enter one numeric face id
	face_id = 0

	# Initialize individual sampling face count
	count = 0
	while(True):
		ret, img = cam.read()
		#img = cv2.flip(img, -1) # flip video image vertically
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		faces = face_detector.detectMultiScale(gray, 1.3, 5)
		for (x,y,w,h) in faces:
			cv2.rectangle(img, (x,y), (x+w,y+h), (255,0,0), 2)     
			count += 1
			# Save the captured image into the datasets folder
			cv2.imwrite(path + str(face_id) + '.' + str(count) + ".jpg", gray[y:y+h,x:x+w])
			cv2.imshow('image', img)
		k = cv2.waitKey(100) & 0xff # Press 'ESC' for exiting video
		if k == 27:
			break
		elif count >= 50: # Take 30 face sample and stop video
			break
	cam.release()
	cv2.destroyAllWindows()

	return render(request,'cam/camera2.html')

def getImagesAndLabels(path):
    imagePaths = [os.path.join(path,f) for f in os.listdir(path)]     
    faceSamples=[]
    ids = []
    for imagePath in imagePaths:
        PIL_img = Image.open(imagePath).convert('L') # convert it to grayscale
        img_numpy = np.array(PIL_img,'uint8')
        id = int(os.path.split(imagePath)[-1].split(".")[1])
        faces = detector.detectMultiScale(img_numpy)
        for (x,y,w,h) in faces:
            faceSamples.append(img_numpy[y:y+h,x:x+w])
            ids.append(id)
    return faceSamples,ids

def md(request):
	faces,ids = getImagesAndLabels(paths)
	recognizer.train(faces, np.array(ids))
	recognizer.write(trainpath)
	recognizer.read(trainpath)
	cascadePath = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
	faceCascade = cv2.CascadeClassifier(cascadePath)
	font = cv2.FONT_HERSHEY_SIMPLEX

	#iniciate id counter
	id = 0

	# names related to ids: example ==> loze: id=1,  etc
	# 이런식으로 사용자의 이름을 사용자 수만큼 추가해준다.
	names = ['yujin']
	

	# Initialize and start realtime video capture
	

	while True:
		cam = cv2.VideoCapture(0,cv2.CAP_DSHOW)
		cam.set(3, 640) # set video widht
		cam.set(4, 480) # set video height

	# Define min window size to be recognized as a face
		minW = 0.1*cam.get(3)
		minH = 0.1*cam.get(4)
		ret, img =cam.read()
		img = cv2.flip(img, 1) # Flip vertically
		gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
		
		faces = faceCascade.detectMultiScale( 
			gray,
			scaleFactor = 1.2,
			minNeighbors = 5,
			minSize = (int(minW), int(minH)),
		)

		for(x,y,w,h) in faces:
			cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)
			id, confidence = recognizer.predict(gray[y:y+h,x:x+w])
			# Check if confidence is less them 100 ==> "0" is perfect match
			if (confidence < 100):
				id = names[id]
				confidence = "  {0}%".format(round(100 - confidence))
			else:
				id = "unknown"
				confidence = "  {0}%".format(round(100 - confidence))
			
			cv2.putText(img, str(id), (x+5,y-5), font, 1, (255,255,255), 2)
			cv2.putText(img, str(confidence), (x+5,y+h-5), font, 1, (255,255,0), 1)  
		cv2.imshow('camera',img) 
		k = cv2.waitKey(10) & 0xff # Press 'ESC' for exiting video
		if k == 27:
			cam.release()
			cv2.destroyAllWindows()
			break
	

class VideoCamera(object):
	def __init__(self):
		self.video = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
		(self.grabbed, self.frame) = self.video.read()
		threading.Thread(target=self.update, args=()).start()

	def __del__(self):
		self.video.release()

	def get_frame(self):
		image = self.frame
		ret, jpeg = cv2.imencode('.jpg', image)
		return jpeg.tobytes()		

	def update(self):
		while True:
			(self.grabbed, self.frame) = self.video.read()

	def take_frame(self):
		now = datetime.now()
		fileName = filePath + now.strftime('%y%m%d_%H%M%S') + '.png'
		print (fileName)
		cv2.imwrite(fileName, self.frame)

		db = Image(image_name=now.strftime('%y%m%d_%H%M%S'), pub_date=timezone.now())
		db.save()




def gen(camera):
	while True:
		frame = camera.get_frame()
		yield(b'--frame\r\n'
			b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def video(request):
    try:
        return StreamingHttpResponse(gen(VideoCamera()), content_type="multipart/x-mixed-replace;boundary=frame")
    except:
        pass

def camera_1(request):
	if request.method == 'POST':
		md(request)

	return render(request, 'cam/camera.html')