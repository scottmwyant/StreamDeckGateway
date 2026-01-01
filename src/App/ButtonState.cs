
namespace App;

// Goal: emit events for button presses, releases, and device wake-ups

// 1. Know when device wakes up
//    > Assume screensaveer will only become active when no buttons are down (Value == 0)
//    > When device wakes up, first event will be a KeyUp (Value == 0)
//    > Is every Value == 0 event a wake up?  No, could be just user releasing all buttons.
//    > Wake up is when you get a Value == 0 event when previous Value was also 0
//    > Need to compare two states to determine wake up when both are 0, it's a wake up.

// 2. Compare each incoming report to the previous report to determine what changed
//    > Assume each event (input buffer) is state change for a single key
//    > Only exception to this is a "wake up" which is described above.
//    > If newValue > oldValue, it's a KeyDown event
//    > If newValue < oldValue, it's a KeyUp event
//    > If newValue == oldValue and both are 0, it's a wake up event
//    > If newValue == oldValue and it's non-zero, log a warning; an assumption is violated.

internal class ButtonState
{
    public int Value { get; } = 0;

    public ButtonState() {}

    public ButtonState(byte[] buffer)
    {
        // Construct an instance of 'ButtonState' using the 512 byte input buffer.
        // The state of the 15 buttons is kept in index 4 through 18 (15 bytes).
        byte[] states = buffer[4..19]; // first is inclusive, second is exclusive

        // Each zero-value byte is a 0, each non-zero byte is a 1.
        // Use that to construct a 15-bit integer value
        for (int i = 0; i < states.Length; i++)
        {
            if (states[i] != 0)
                Value |= (1 << i);
        }
    }

    /// <summary>
    /// Compares this state with a previous state to determine the event type and target button.
    /// </summary>
    /// <param name="previousState">The previous button state</param>
    /// <returns>A ButtonEvent describing the change, or null if no single-button change detected</returns>
    public ButtonEventArgs? CompareWith(ButtonState previousState)
    {
        // XOR to find bits that changed
        int changed = Value ^ previousState.Value;
        
        // If no bits changed, check for wake-up scenario
        if (changed == 0)
        {
            if (Value == 0 && previousState.Value == 0)
            {
                return new ButtonEventArgs { EventType = ButtonEventType.WakeUp, Target = null };
            }
            
            // Both states are identical and non-zero - warning case
            return null;
        }

        // Find which button changed (should only be one bit different)
        int buttonIndex = GetChangedButtonIndex(changed);
        if (buttonIndex == -1)
        {
            // Multiple buttons changed - unexpected
            return null;
        }

        // Determine if it's a key down or key up
        var eventType = ((Value & (1 << buttonIndex)) != 0) ? ButtonEventType.KeyDown : ButtonEventType.KeyUp;

        return new ButtonEventArgs { EventType = eventType, Target = buttonIndex + 1 }; // Buttons are 1-indexed
    }

    private int GetChangedButtonIndex(int changedBits)
    {
        // Verify only one bit changed
        if ((changedBits & (changedBits - 1)) != 0)
        {
            // Multiple bits set - not a single button change
            return -1;
        }

        // Find the position of the single set bit
        return System.Numerics.BitOperations.TrailingZeroCount(changedBits);
    }
}
