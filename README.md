# video-frame-selector
Meta-tool that presents frames from a video to image analysis frameworks and uses the predictions to determine 
whether to use a frame or not.


## Installation

* create virtual environment

  ```commandline
  virtualenv -p /usr/bin/python3.7 venv
  ```
  
* install library

  ```commandline
  ./venv/bin/pip install video-frame-selector
  ```

## Supported formats

* Input

  * webcam
  * videos
  
* Image analysis output

  * [ROI CSV](https://github.com/waikato-ufdl/wai-annotations-roi)
  
* Output

  * JPG files (using frame number as file name)
  * MJPG video (use either .avi or .mkv as file extension for the container) 


## Command-line options

```
usage: vfs-process [-h] --input FILE_OR_ID --input_type {video,webcam}
                   [--nth_frame INT] [--max_frames INT] [--from_frame INT]
                   [--to_frame INT] [--analysis_input DIR]
                   [--analysis_tmp DIR] [--analysis_output DIR]
                   [--analysis_timeout SECONDS] [--analysis_type {rois_csv}]
                   [--analysis_keep_files] [--min_score FLOAT]
                   [--required_labels LIST] [--excluded_labels LIST]
                   [--poll_interval POLL_INTERVAL] --output DIR_OR_FILE
                   --output_type {jpg,mjpg} [--output_format FORMAT]
                   [--output_tmp DIR] [--output_fps FORMAT]
                   [--crop_to_content] [--crop_margin INT]
                   [--crop_min_width INT] [--crop_min_height INT]
                   [--output_metadata] [--progress INT] [--verbose]

Tool for replaying videos or grabbing frames from webcam, presenting it to an
image analysis framework to determine whether to include the frame in the
output.

optional arguments:
  -h, --help            show this help message and exit
  --input FILE_OR_ID    the video file to read or the webcam ID (default:
                        None)
  --input_type {video,webcam}
                        the input type (default: None)
  --nth_frame INT       every nth frame gets presented to the analysis process
                        (default: 10)
  --max_frames INT      the maximum number of processed frames before exiting
                        (<=0 for unlimited) (default: 0)
  --from_frame INT      the starting frame (incl.); ignored if <= 0 (default:
                        -1)
  --to_frame INT        the last frame to process (incl.); ignored if <= 0
                        (default: -1)
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
  --analysis_type {rois_csv}
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
                        some metadata when output frame images (default:
                        False)
  --progress INT        every nth frame a progress is being output (in verbose
                        mode) (default: 100)
  --verbose             for more verbose output (default: False)
```
