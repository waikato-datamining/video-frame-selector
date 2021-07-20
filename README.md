# video-frame-selector
Meta-tool that presents frames from a video to object detection frameworks and uses the predictions to determine 
whether to use a frame or not.

## Command-line options

```
usage: vfs-process [-h] --input FILE_OR_ID --input_type TYPE [--nth_frame INT]
                   [--max_frames INT] [--analysis_input DIR]
                   [--analysis_tmp DIR] [--analysis_output DIR]
                   [--analysis_timeout SECONDS] [--analysis_type TYPE]
                   [--min_score FLOAT] [--required_labels LIST]
                   [--excluded_labels LIST] --output DIR_OR_FILE --output_type
                   TYPE [--output_format FORMAT] [--output_tmp DIR]
                   [--output_fps FORMAT] [--verbose]

Tool for replaying videos or grabbing frames from webcam, presenting it to an
image analysis framework to determine whether to include the frame in the
output.

optional arguments:
  -h, --help            show this help message and exit
  --input FILE_OR_ID    the video file to read or the webcam ID (default:
                        None)
  --input_type TYPE     the input type (default: None)
  --nth_frame INT       every nth frame gets presented to the analysis process
                        (default: 10)
  --max_frames INT      the maximum number of processed frames before exiting
                        (<=0 for unlimited) (default: 0)
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
  --analysis_type TYPE  the type of output the analysis process generates
                        (default: rois_csv)
  --min_score FLOAT     the minimum score that a prediction must have
                        (default: 0.0)
  --required_labels LIST
                        the comma-separated list of labels that the analysis
                        output must contain (with high enough scores)
                        (default: )
  --excluded_labels LIST
                        the comma-separated list of labels that the analysis
                        output must not contain (with high enough scores)
                        (default: )
  --output DIR_OR_FILE  the output directory or file for storing the selected
                        frames (default: None)
  --output_type TYPE    the type of output to generate (default: None)
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
  --verbose             for more verbose output (default: False)
```