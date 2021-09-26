Meta-tool that presents frames from a video to image analysis frameworks and uses the predictions to determine
whether to use a frame or not.

Frames can be presented as files (*file-polling-based*) with the predictions
then being read from files that the image analysis framework generated.

Alternatively, a Redis (https://redis.io/) backend can be used (*redis-based*),
to broadcast the images as JPG bytes and then listening on another channel
for the predictions to come through. This approach avoids wearing out disks.

Project page:

https://github.com/waikato-datamining/video-frame-selector
