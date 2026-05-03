# arduino-stream-deck
Arduino code for DIY stream deck keyboard with pagination, local mapping (on PC), and multiple keystrokes support

<img width="800" alt="image" src="https://raw.githubusercontent.com/dayeggpi/stream-deck-keybinding/refs/heads/main/streamdeck.jpg"/>

# What's different 

I've built my own stream deck following examples you can see online: 
1. https://github.com/SuperMakeSomething/diy-stream-deck
2. https://github.com/atkaper/macro-keypad
3. https://legeeketsonmarteau.fr/stream-deck-diy/

I used the typical code as shared online however I wanted extra features :

1. Pagination to use more buttons
2. Support for multiple keybindings (e.g. not just "F10" but also "CTRL+SHIT+F10"
3. Support for key assignment on PC and not in arduino code, to allow for easy updates without need to recompile/upload code to arduino

I have 4 buttons to which I can bind keys, and one button for pagination.

I added a led bar that would show me in which page I am. Visually I can therefore have 10 pages, but if you add two extra leds that act as visual indicators for set of pages, you can extend this to 20 (and apply same logic for more).


# Steps

1. Build your stream deck
2. Upload the arduino code (Take the ino file, place it in a folder, open your Arduino IDE, and upload the code to it. Be sure to also install the needed libraries first (such as the Grove_LED_Bar for example))
3. Prepare your settings.ini (see below)
4. Run the flash_config.py file (it will send the new config as per settings.ini to the arduino)


# Notes

The arduino code, and settings.ini accepts 4 buttons and 4 pages (I don't need more). Extend as per needs.

# Settings.ini config

Follow the example of attahced file.

Note that it accepts following format per button: KEY  or  MOD+KEY  or  MOD+MOD+KEY

Modifiers can be CTRL, SHIFT, ALT, GUI (Win key), RCTRL, RSHIFT, RALT, RGUI  (right-side variants)

Special keys: F1-F24, ESC, TAB, ENTER, SPACE, BACKSPACE, DELETE, INSERT, HOME, END, PAGE_UP, PAGE_DOWN, UP, DOWN, LEFT, RIGHT, CAPS_LOCK, PRINT_SCREEN

Regular characters: a-z, 0-9, and symbols use their literal character


Examples:
```
  Button1 = F21
  Button1 = CTRL+ALT+d
  Button1 = CTRL+SHIFT+k
  Button1 = CTRL+z
  Button1 = SPACE
```
