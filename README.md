# gesture-audio-control

A gesture audio control program inspired by BMW's iDrive System. Built upon a trained gesture recognition model developed by Kazuhito00 (https://github.com/Kazuhito00/hand-gesture-recognition-using-mediapipe)

The program recognize the following gestures:

* `Clockwise rotation (index finger)` Increase the volume.

* `Counter-clockwise rotation (index finger)` Decrease the volume.

* `Open hand` Play audio.

* `Closed hand` Pause audio.



## Installation

Clone the project:

```
git clone https://github.com/Irreq/gesture-audio-control.git
```

Move to the project folder:

```
cd gesture-audio-control
```

Install dependencies:

```
pip3 install requirements.txt
```


## Setup

The program should work out-of-the-box.

## Usage
To *start* the program:

```
python3 app.py
```

The program can be used with a specific camera:

```
python3 app.py --device 2
```

## TODO

Fix support for Windows and Darwin users. Following files:
`pygac/audio/darwin.py` and `pygac/audio/windows.py`.

## Contributing

### Want to Help?

All help is appreciated.
