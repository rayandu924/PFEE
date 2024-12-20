import asyncio
from aiortc.contrib.media import MediaPlayer

async def test_media_player():
    player = MediaPlayer(
        "video=USB Camera", 
        format="dshow", 
        options={
            "rtbufsize": "10485760",
            "framerate": "2",
            "video_size": "160x120"
        }
    )

    if player.video:
        print("Video track initialized successfully")
        frame = await player.video.recv()
        print(f"Received frame: {frame}")
    else:
        print("Failed to initialize video track")

    await player.stop()

asyncio.run(test_media_player())
