For rtsp :
$ ffmpeg -re -f lavfi -i color=size=1280x720:rate=30:color=black \
    -vf "drawtext=text='%{pts\\:hms}':fontsize=24:fontcolor=white:x=10:y=10" \
    -c:v libx264 -profile:v baseline -pix_fmt yuv420p -f rtsp -rtsp_transport udp rtsp://localhost:8554/monflux

lesstency/rtsp-server$ ./rtsp-simple-server 


in /usr/local/etc/janus/janus.plugin.streaming.jcfg modify 
"rtsp-test: {
    type = "rtsp"
    id = 4
    description = "Local RTSP Stream"
    audio = false
    video = true
    url = "rtsp://127.0.0.1:8554/monflux"
	rtsp_reconnect_delay = 5
	rtsp_session_timeout = 0
	rtsp_timeout = 10
	rtsp_conn_timeout = 5
}
"

~/lesstency/janus-gateway$ janus # launch janus

chrome://webrtc-internals/ # check metrics

