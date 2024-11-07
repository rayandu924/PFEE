TEST - Create a RTSP TEST FLUX ========================================

# Téléchargez la dernière version depuis GitHub
wget https://github.com/aler9/rtsp-simple-server/releases/download/v0.17.7/rtsp-simple-server_v0.17.7_linux_amd64.tar.gz

# Extrayez l'archive
tar xvf rtsp-simple-server_v0.17.7_linux_amd64.tar.gz

# Déplacez-vous dans le répertoire extrait
cd rtsp-simple-server

# Lancez le serveur
./rtsp-simple-server

# Sur un autre terminal lancer le flux 
ffmpeg -re -f lavfi -i color=size=1280x720:rate=30:color=black \
    -vf "drawtext=text='%{pts\\:hms}':fontsize=24:fontcolor=white:x=10:y=10" \
    -c:v libx264 -profile:v baseline -pix_fmt yuv420p -f rtsp rtsp://localhost:8554/monflux

================================================


create virtual environment : python3 -m venv venv

update requirements.txt : pip freeze > requirements.txt

download requirements.txt : pip install -r requirements.txt

activate virtual environment : source venv/bin/activate
 
install pycairo : 
sudo apt-get install -y pkg-config libcairo2-dev libgirepository1.0-dev python3-dev

install typelib :
sudo apt-get install gir1.2-gst-plugins-base-1.0 gir1.2-gstreamer-1.0
sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gir1.2-gst-rtsp-server-1.0

(reinstall pygobject if the first installation failed(je sais pas si ca fail ou pas 1st time a revoir)):
pip install pygobject

install gstreamer et ses plugins : 
sudo apt-get install libgstreamer1.0-dev gstreamer1.0-plugins-base \
gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
gstreamer1.0-plugins-ugly gstreamer1.0-libav

stream a rtsp test live :
gst-launch-1.0 \
videotestsrc pattern=black ! \
video/x-raw,width=640,height=480,framerate=30/1 ! \
clockoverlay time-format="%H:%M:%S" halignment=center valignment=center text="Compteur : " ! \
x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! \
rtph264pay config-interval=1 name=pay0 pt=96 ! \
udpsink host=127.0.0.1 port=5000



