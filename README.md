# Sign_Language_Translation

Required packages (use pip install):

- opencv-python
- tensorflow (you must have tensorflow >= 2.2)
- tensorflow_hub


To run CNN feature extractor:

1. cd to your models subdirectory
2. Edit config760.json and set indir and outdir to the directory your videos are in and the dir you want to put the feature files into.
3. Also in config760.json, setting "crop_type": "T" (default) means crop vids to the top (front view) of each image and "B" crops to the bottom (side view). To get both you need to run the program twice, once for each crop type.
4. python extract_features.py
5. Ignore the various tensorflow messages, eventually the program will start processing videos. Each vid takes around 10 secs to process on my machine.



