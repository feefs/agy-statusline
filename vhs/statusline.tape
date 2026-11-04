Output vhs/demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1160
Set Height 130
Set Padding 16
Set Margin 20
Set MarginFill "#cba6f7"
Set BorderRadius 10
Set Theme "Catppuccin Mocha"
Set CursorBlink false
Set Framerate 10

Hide
Type "python3 -m vhs.demo"
Enter
Sleep 200ms
Show

# Record 4 frames at 3s each (demo.py sleeps longer on the last frame as a buffer)
Sleep 12s
