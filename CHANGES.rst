Changelog
=========

0.0.9 (2022-01-27)
------------------

- added support for pruning frames that do not exhibit enough change over the previous one
  (`--prune`, `--bw_threshold`, `--change_threshold`)


0.0.8 (2021-11-02)
------------------

- `process.py` and `process_redis.py` now allow iterating through images (.jpg, .png) in a directory
- `process_redis.py` now handles predictions in bytes or str


0.0.7 (2021-09-27)
------------------

- `process.py` now adheres to the `--output_metadata` flag
- `process_redis.py` allows processing of frames via Redis backend


0.0.6 (2021-08-05)
------------------

- `frames processed` output is now always being output
- added logging output for frame file and metadata file in `verbose` mode


0.0.5 (2021-08-05)
------------------

- added `--output_metadata` flag that stores information on predictions and cropping when outputting frames


0.0.4 (2021-08-03)
------------------

- added `--crop_to_content` flag that crops the frames to the bounding boxes
  (only when not generating an output video)
- added `--crop_margin` option to enforce a buffer around cropped region
- added `--crop_min_width` and `--crop_min_height` options to enforce a minimum width/height


0.0.3 (2021-08-02)
------------------

- added `--poll_interval` option (https://github.com/waikato-datamining/video-frame-selector/issues/2)
- added logging output for when writing image to disk


0.0.2 (2021-07-30)
------------------

- fixed `return` statement in `process_image` method
- added more debugging output
- added `--analysis_keep_files` option for debugging purposes, which won't delete the output
  of the image analysis framework
- added options for defining a frame window (`--from_frame`, `--to_frame`)


0.0.1 (2021-07-21)
------------------

- initial release
