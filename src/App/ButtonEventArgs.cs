namespace App;

public class ButtonEventArgs : EventArgs
{
    public ButtonEventType EventType { get; set; }
    public int? Target { get; set; } // 0-14 for button index, null for wake-up
}