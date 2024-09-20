/* global iceServers:readonly, Janus:readonly, server:readonly */
var server = "http://localhost:8088/janus";  // Your Janus server URL
var iceServers = [{ urls: "stun:stun.l.google.com:19302" }];  // Example ICE server

var janus = null;
var streaming = null;   
var opaqueId = "streamingtest-" + Janus.randomString(12);

var streamsList = {};
var selectedStream = null;

$(document).ready(function () {
    // Initialize the Janus library
    Janus.init({
        debug: "all",  // Enable all levels of debug
        callback: function () {
            console.log("Janus initialized");
            // Start demo on button click
            $('#start').one('click', function () {
                $(this).attr('disabled', true).unbind('click');
                if (!Janus.isWebrtcSupported()) {
                    alert("No WebRTC support... ");
                    return;
                }
                // Create Janus session
                janus = new Janus({
                    server: server,
                    iceServers: iceServers,
                    success: function () {
                        console.log("Janus session created successfully");
                        // Attach to Streaming plugin
                        janus.attach({
                            plugin: "janus.plugin.streaming",
                            opaqueId: opaqueId,
                            success: function (pluginHandle) {
                                streaming = pluginHandle;
                                console.log("Streaming plugin attached! (" + streaming.getPlugin() + ", id=" + streaming.getId() + ")");
                                
                                // Setup streaming session and stream list updater
                                $('#update-streams').click(updateStreamsList);
                                updateStreamsList(); // Call immediately to list streams
                            },
                            error: function (error) {
                                console.error("Error attaching plugin: ", error);
                                alert("Error attaching plugin: " + error);
                            },
                            onmessage: function (msg, jsep) {
                                console.log("Received message from Janus plugin:", msg);
                                if (msg["error"]) {
                                    alert(msg["error"]);
                                    return;
                                }
                                // Handle SDP offer/answer negotiation
                                if (jsep !== undefined && jsep !== null) {
                                    console.log("Received SDP from Janus, type: " + jsep.type);
                                    console.log("SDP content:\n" + jsep.sdp);  // Log SDP to see codec and other negotiation details
                                    
                                    streaming.createAnswer({
                                        jsep: jsep,
                                        tracks: [{ type: 'video', capture: false, recv: true }],
                                        success: function (jsep) {
                                            console.log("Created SDP answer successfully");
                                            console.log("SDP Answer content:\n" + jsep.sdp);  // Log the answer SDP for debugging
                                            
                                            var body = { request: "start" };
                                            streaming.send({ message: body, jsep: jsep });
                                            $('#watch').html("Stop").removeAttr('disabled').unbind('click').click(stopStream);
                                        },
                                        error: function (error) {
                                            console.error("WebRTC error while creating answer:", error);
                                            alert("WebRTC error: " + error.message);
                                        }
                                    });
                                }
                            },
                            onremotetrack: function (track, mid, on) {
                                if (!on) {
                                    console.log("Remote track removed (mid=" + mid + ")");
                                    return; // Track removed
                                }
                            
                                console.log("New remote track added (mid=" + mid + ")", track);
                                console.log("Track kind: " + track.kind);  // Log track type (video/audio)
                                console.log("Track readyState: " + track.readyState);  // Check if track is live
                                
                                // Create a MediaStream and attach it to the video element
                                var stream = new MediaStream([track]);
                                $('#videos').append('<video id="remotevideo" width="640" height="480" autoplay playsinline></video>');
                                const videoElement = $('#remotevideo').get(0);
                                Janus.attachMediaStream(videoElement, stream);
                            },
                            iceState: function (state) {
                                console.log("ICE connection state changed to: " + state);  // Log ICE connection states (checking, connected, completed, etc.)
                            },
                            mediaState: function (medium, receiving, mid) {
                                console.log("Janus " + (receiving ? "started" : "stopped") + " receiving " + medium + " (mid=" + mid + ")");  // Log media state
                            },
                            webrtcState: function (isConnected) {
                                console.log("WebRTC PeerConnection " + (isConnected ? "connected" : "disconnected") + " to Janus backend");
                            },
                            oncleanup: function () {
                                console.log("Cleanup notification received");
                                $('#remotevideo').remove();
                            }
                        });
                    },
                    error: function (error) {
                        console.error("Error initializing Janus: ", error);
                        alert("Error initializing Janus: " + error);
                    },
                    destroyed: function () {
                        console.log("Janus session destroyed");
                        window.location.reload();
                    }
                });
            });
        }
    });
});

// Fetch and update the list of available streams
function updateStreamsList() {
    console.log("Updating list of available streams");
    $('#update-streams').unbind('click').addClass('fa-spin');
    var body = { request: "list" };
    streaming.send({
        message: body,
        success: function (result) {
            console.log("Streams list received:", result);
            $('#update-streams').removeClass('fa-spin').unbind('click').click(updateStreamsList);
            if (!result || !result.list) {
                alert("No streams available");
                return;
            }
            streamsList = result.list;
            $('#streamslist').empty();
            streamsList.forEach(function (stream) {
                console.log("Available stream: " + stream.description + " (ID: " + stream.id + ")");
                $('#streamslist').append(`<a class="dropdown-item" href="#" id="${stream.id}">${stream.description}</a>`);
            });
            $('#streamslist a').unbind('click').click(function () {
                selectedStream = $(this).attr("id");
                console.log("Selected stream ID: " + selectedStream);
                $('#streamset').html($(this).html());
                $('#watch').removeAttr('disabled').unbind('click').click(startStream);
            });
        }
    });
}

// Start the selected stream
function startStream() {
    console.log("Starting stream with ID: " + selectedStream);
    if (!selectedStream) {
        alert("Please select a stream from the list");
        return;
    }
    var body = { request: "watch", id: parseInt(selectedStream) || selectedStream };
    streaming.send({ message: body });
}

// Stop the stream and hang up
function stopStream() {
    console.log("Stopping stream with ID: " + selectedStream);
    var body = { request: "stop" };
    streaming.send({ message: body });
    streaming.hangup();
    $('#watch').attr('disabled', true);
}