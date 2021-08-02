Changelog
=========

0.0.4 (????-??-??)
------------------

- added `--crop_to_content` flag that crops the frames to the bounding boxes
  (only when not generating an output video)


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
