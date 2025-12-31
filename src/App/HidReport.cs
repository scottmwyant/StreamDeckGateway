using HidSharp;

namespace App;

internal static class HidReport
{
    public static int[] GetKeysDown(byte[] buffer)
    {
        const int startIndex = 4;
        const int buttonCount = 15;
        var keysDown = new List<int>();
        for (int i = startIndex; i <= startIndex + buttonCount; i++)
        {
            if (buffer[i] != 0)
                keysDown.Add(i - startIndex + 1);
        }
        return keysDown.ToArray();
    }
    public static int GetFirstKeyDown(byte[] buffer)
    {
        const int startIndex = 4;
        const int buttonCount = 15;
        for (int i = startIndex; i <= startIndex + buttonCount; i++)
        {
            if (buffer[i] != 0)
                return i - startIndex + 1;
        }
        return 0;
    }

}
