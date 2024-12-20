# video-frame-selector
Meta-tool that presents frames from a video to image analysis frameworks and uses the predictions to determine 
whether to use a frame or not.

Frames can be presented as files (*file-polling-based*) with the predictions
then being read from files that the image analysis framework generated.

Alternatively, a [Redis](https://redis.io/) backend can be used (*redis-based*),
to broadcast the images as JPG bytes and then listening on another channel
for the predictions to come through. This approach avoids wearing out disks. 

Rather than just processing every n-th frame, a simple pruning mechanism can
be employed which discards frames that are too similar.


## Installation

* create virtual environment

  ```bash
  virtualenv -p /usr/bin/python3.7 venv
  ```
  
* install library

  ```bash
  ./venv/bin/pip install video_frame_selector
  ```

## Supported formats

* Input

  * directory with images (.jpg, .png)
  * webcam
  * videos
  
* Image analysis output

  * [ROI CSV](https://github.com/waikato-ufdl/wai-annotations-roi)
  * [OPEX JSON](https://github.com/WaikatoLink2020/objdet-predictions-exchange-format)
  
* Output

  * JPG files (using frame number as file name) - optional metadata file in YAML format 
  * MJPG video (use either .avi or .mkv as file extension for the container) 


## Command-line options

### File-polling based

```
usage: vfs-process [-h] --input DIR_OR_FILE_OR_ID --input_type
                   {image_dir,video,webcam} [--nth_frame INT]
                   [--max_frames INT] [--from_frame INT] [--to_frame INT]
                   [--prune] [--bw_threshold INT] [--change_threshold FLOAT]
                   [--analysis_input DIR] [--analysis_tmp DIR]
                   [--analysis_output DIR] [--analysis_timeout SECONDS]
                   [--analysis_type {rois_csv,opex_json}]
                   [--analysis_keep_files] [--min_score FLOAT]
                   [--required_labels LIST] [--excluded_labels LIST]
                   [--poll_interval POLL_INTERVAL] --output DIR_OR_FILE
                   --output_type {jpg,mjpg} [--output_format FORMAT]
                   [--output_tmp DIR] [--output_fps FORMAT]
                   [--crop_to_content] [--crop_margin INT]
                   [--crop_min_width INT] [--crop_min_height INT]
                   [--output_metadata] [--progress INT] [--keep_original]
                   [--verbose]

Tool for replaying videos or grabbing frames from webcam, presenting it to an
image analysis framework to determine whether to include the frame in the
output.

optional arguments:
  -h, --help            show this help message and exit
  --input DIR_OR_FILE_OR_ID
                        the dir with images, video file to read or the webcam
                        ID (default: None)
  --input_type {image_dir,video,webcam}
                        the input type (default: None)
  --nth_frame INT       every nth frame gets presented to the analysis process
                        (default: 10)
  --max_frames INT      the maximum number of processed frames before exiting
                        (<=0 for unlimited) (default: 0)
  --from_frame INT      the starting frame (incl.); ignored if <= 0 (default:
                        -1)
  --to_frame INT        the last frame to process (incl.); ignored if <= 0
                        (default: -1)
  --prune               whether to prune the images if not enough change
                        (default: False)
  --bw_threshold INT    The threshold (0-255) for the black/white conversion
                        (requires --prune) (default: 128)
  --change_threshold FLOAT
                        The threshold (0.0-1.0) for the change detection
                        (requires --prune) (default: 0.0)
  --analysis_input DIR  the input directory used by the image analysis
                        process; if not provided, all frames get accepted
                        (default: None)
  --analysis_tmp DIR    the temporary directory to place the images in before
                        moving them into the actual input directory (to avoid
                        race conditions) (default: None)
  --analysis_output DIR
                        the output directory used by the image analysis
                        process (default: None)
  --analysis_timeout SECONDS
                        the maximum number of seconds to wait for the image
                        analysis to finish processing (default: 10)
  --analysis_type {rois_csv,opex_json}
                        the type of output the analysis process generates
                        (default: rois_csv)
  --analysis_keep_files
                        whether to keep the analysis files rather than
                        deleting them (default: False)
  --min_score FLOAT     the minimum score that a prediction must have
                        (default: 0.0)
  --required_labels LIST
                        the comma-separated list of labels that the analysis
                        output must contain (with high enough scores)
                        (default: None)
  --excluded_labels LIST
                        the comma-separated list of labels that the analysis
                        output must not contain (with high enough scores)
                        (default: None)
  --poll_interval POLL_INTERVAL
                        interval in seconds for polling for result files
                        (default: 0.1)
  --output DIR_OR_FILE  the output directory or file for storing the selected
                        frames (use .avi or .mkv for videos) (default: None)
  --output_type {jpg,mjpg}
                        the type of output to generate (default: None)
  --output_format FORMAT
                        the format string for the images, see
                        https://docs.python.org/3/library/stdtypes.html#old-
                        string-formatting (default: %06d.jpg)
  --output_tmp DIR      the temporary directory to write the output images to
                        before moving them to the output directory (to avoid
                        race conditions with processes that pick up the
                        images) (default: None)
  --output_fps FORMAT   the frames per second to use when generating a video
                        (default: 25)
  --crop_to_content     whether to crop the frame to the detected content
                        (default: False)
  --crop_margin INT     the margin in pixels to use around the determined crop
                        region (default: 0)
  --crop_min_width INT  the minimum width for the cropped content (default: 2)
  --crop_min_height INT
                        the minimum height for the cropped content (default:
                        2)
  --output_metadata     whether to output a YAML file alongside the image with
                        some metadata when outputting frame images (default:
                        False)
  --progress INT        every nth frame a progress message is output on stdout
                        (default: 100)
  --keep_original       keeps the original file name when processing an image
                        dir (default: False)
  --verbose             for more verbose output (default: False)
```


### Redis-based

```
usage: vfs-process-redis [-h] --input DIR_OR_FILE_OR_ID --input_type
                         {image_dir,video,webcam} [--nth_frame INT]
                         [--max_frames INT] [--from_frame INT]
                         [--to_frame INT] [--prune] [--bw_threshold INT]
                         [--change_threshold FLOAT] [--redis_host HOST]
                         [--redis_port PORT] [--redis_db DB] --redis_out
                         CHANNEL --redis_in CHANNEL [--redis_timeout SECONDS]
                         [--analysis_type {rois_csv,opex_json}]
                         [--min_score FLOAT] [--required_labels LIST]
                         [--excluded_labels LIST] --output DIR_OR_FILE
                         --output_type {jpg,mjpg} [--output_format FORMAT]
                         [--output_tmp DIR] [--output_fps FORMAT]
                         [--crop_to_content] [--crop_margin INT]
                         [--crop_min_width INT] [--crop_min_height INT]
                         [--output_metadata] [--progress INT]
                         [--keep_original] [--verbose]

Tool for replaying videos or grabbing frames from webcam, presenting it to an
image analysis framework to determine whether to include the frame in the
output. Uses Redis to exchange data.

optional arguments:
  -h, --help            show this help message and exit
  --input DIR_OR_FILE_OR_ID
                        the dir with images, video file to read or the webcam
                        ID (default: None)
  --input_type {image_dir,video,webcam}
                        the input type (default: None)
  --nth_frame INT       every nth frame gets presented to the analysis process
                        (default: 10)
  --max_frames INT      the maximum number of processed frames before exiting
                        (<=0 for unlimited) (default: 0)
  --from_frame INT      the starting frame (incl.); ignored if <= 0 (default:
                        -1)
  --to_frame INT        the last frame to process (incl.); ignored if <= 0
                        (default: -1)
  --prune               whether to prune the images if not enough change
                        (default: False)
  --bw_threshold INT    The threshold (0-255) for the black/white conversion
                        (requires --prune) (default: 128)
  --change_threshold FLOAT
                        The threshold (0.0-1.0) for the change detection
                        (requires --prune) (default: 0.0)
  --redis_host HOST     The redis server to connect to (default: localhost)
  --redis_port PORT     The port the redis server is listening on (default:
                        6379)
  --redis_db DB         The redis database to use (default: 0)
  --redis_out CHANNEL   The redis channel to send the frames to (default:
                        None)
  --redis_in CHANNEL    The redis channel to receive the predictions on
                        (default: None)
  --redis_timeout SECONDS
                        the maximum number of seconds to wait for the image
                        analysis to finish processing (default: 10)
  --analysis_type {rois_csv,opex_json}
                        the type of output the analysis process generates
                        (default: rois_csv)
  --min_score FLOAT     the minimum score that a prediction must have
                        (default: 0.0)
  --required_labels LIST
                        the comma-separated list of labels that the analysis
                        output must contain (with high enough scores)
                        (default: None)
  --excluded_labels LIST
                        the comma-separated list of labels that the analysis
                        output must not contain (with high enough scores)
                        (default: None)
  --output DIR_OR_FILE  the output directory or file for storing the selected
                        frames (use .avi or .mkv for videos) (default: None)
  --output_type {jpg,mjpg}
                        the type of output to generate (default: None)
  --output_format FORMAT
                        the format string for the images, see
                        https://docs.python.org/3/library/stdtypes.html#old-
                        string-formatting (default: %06d.jpg)
  --output_tmp DIR      the temporary directory to write the output images to
                        before moving them to the output directory (to avoid
                        race conditions with processes that pick up the
                        images) (default: None)
  --output_fps FORMAT   the frames per second to use when generating a video
                        (default: 25)
  --crop_to_content     whether to crop the frame to the detected content
                        (default: False)
  --crop_margin INT     the margin in pixels to use around the determined crop
                        region (default: 0)
  --crop_min_width INT  the minimum width for the cropped content (default: 2)
  --crop_min_height INT
                        the minimum height for the cropped content (default:
                        2)
  --output_metadata     whether to output a YAML file alongside the image with
                        some metadata when outputting frame images (default:
                        False)
  --progress INT        every nth frame a progress message is output on stdout
                        (default: 100)
  --keep_original       keeps the original file name when processing an image
                        dir (default: False)
  --verbose             for more verbose output (default: False)
```

## Examples

### File-polling based

In the following, an example of how to use the *video-frame-selector* to feed images to a 
file-based [detectron2](https://github.com/waikato-datamining/pytorch/tree/master/detectron2) 
model that runs in a docker container.

Directory structure:

```
/some/where
|
|- cache (pytorch cache)
|
|- data (contains videos and detectron training data)
|
|- output (detectron2 models etc)
|
|- d2 (detectron work area)
|  |
|  +- in
|  |
|  +- tmp
|  |
|  +- out
|
|- vfs (vfs work area)
|  |
|  +- in
|  |
|  +- tmp
|  |
|  +- out (contains frames to keep)
```

Running [detectron2](https://github.com/waikato-datamining/pytorch/tree/master/detectron2) 
to detect farm animals (Goat, Cow, Chicken): 

```bash
docker run --gpus=all --shm-size 8G -u $(id -u):$(id -g) -e USER=$USER \
    -v /some/where:/opt/projects \
    -v /some/where/cache:/.torch \
    -it public.aml-repo.cms.waikato.ac.nz:443/pytorch/detectron2:0.5

DATASET=/opt/projects/data/animal_farm
OUTPUT=/opt/projects/output/animal_farm
CONFIG=mask_rcnn_R_50_FPN_1x.yaml 

d2_predict \
  --model $OUTPUT/model_final.pth \
  --config $OUTPUT/$CONFIG \
  --labels $DATASET/train/labels.txt \
  --prediction_in /opt/projects/d2/in/ \
  --prediction_tmp /opt/projects/d2/tmp/ \
  --prediction_out /opt/projects/d2/out/ \
  --delete_input \
  --max_files 10 \
  --use_watchdog \
  --continuous
```

Feeding in images from a video, but only keeping frames with *Goat* detections with a score of at least 0.8:

```bash
vfs-process \ 
  --input "/some/where/data/my_farm.avi" \
  --input_type video \
  --nth_frame 10 \
  --analysis_input /some/where/d2/in \
  --analysis_tmp /some/where/vfs/tmp \
  --analysis_output /some/where/d2/out \
  --min_score 0.8 \
  --required_labels Goat \
  --output /some/where/vfs/out \
  --output_type jpg \
  --verbose \
  --progress 100 \
  --poll_interval 0.01 \
  --crop_to_content \
  --crop_margin 50 \
  --crop_min_width 600 \
  --crop_min_height 600 \
  --output_metadata
```

### Redis-based

In the following, an example of how to use the *video-frame-selector* to feed images to a 
redis-based [detectron2](https://github.com/waikato-datamining/pytorch/tree/master/detectron2) 
model that runs in a docker container. 

Of course, a Redis instance must be running as well. This example assumes the instance to
be running on `localhost` and default port `6379`.

Directory structure:

```
/some/where
|
|- cache (pytorch cache)
|
|- data (contains videos and detectron training data)
|
|- output (detectron2 models etc)
```

Running [detectron2](https://github.com/waikato-datamining/pytorch/tree/master/detectron2) 
to detect farm animals (Goat, Cow, Chicken): 

```bash
docker run --gpus=all --shm-size 8G -u $(id -u):$(id -g) -e USER=$USER \
    -v /some/where:/opt/projects \
    -v /some/where/cache:/.torch \
    -it public.aml-repo.cms.waikato.ac.nz:443/pytorch/detectron2:0.5

DATASET=/opt/projects/data/animal_farm
OUTPUT=/opt/projects/output/animal_farm
CONFIG=mask_rcnn_R_50_FPN_1x.yaml 

d2_predict_redis \
  --model $OUTPUT/model_final.pth \
  --config $OUTPUT/$CONFIG \
  --labels $DATASET/train/labels.txt \
  --redis_in images \
  --redis_out predictions
```

Feeding in images from a video, but only keeping frames with *Goat* detections with a score of at least 0.8:

```bash
vfs-process-redis \ 
  --input "/some/where/data/my_farm.avi" \
  --input_type video \
  --nth_frame 10 \
  --redis_out images \
  --redis_in predictions \
  --analysis_type opex_json \
  --min_score 0.8 \
  --required_labels Goat \
  --output /some/where/vfs/out \
  --output_type jpg \
  --verbose \
  --progress 100 \
  --crop_to_content \
  --crop_margin 50 \
  --crop_min_width 600 \
  --crop_min_height 600 \
  --output_metadata
```
