namespace App;

public record ButtonEventArgs
{
    public EventType EventType { get; set; }
    public int? Target { get; set; } // 0-14 for button index, null for wake-up
}