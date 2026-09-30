using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Text;

namespace ScoutPricing
{
    public sealed class NativeSqlite : IDisposable
    {
        private const int OpenReadWrite = 2;
        private const int OpenCreate = 4;
        private readonly bool windows;
        private IntPtr database;

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        private delegate int WindowsRowCallback(IntPtr context, int count, IntPtr values, IntPtr names);

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        private delegate int MacRowCallback(IntPtr context, int count, IntPtr values, IntPtr names);

        private static class Windows
        {
            private const string Library = "winsqlite3.dll";

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern int sqlite3_open_v2(byte[] filename, out IntPtr database, int flags, IntPtr vfs);

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern int sqlite3_busy_timeout(IntPtr database, int milliseconds);

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern int sqlite3_exec(IntPtr database, byte[] sql, WindowsRowCallback callback, IntPtr context, out IntPtr error);

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern void sqlite3_free(IntPtr pointer);

            [DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
            [DllImport(Library, CallingConvention = CallingConvention.StdCall, ExactSpelling = true)]
            internal static extern int sqlite3_close_v2(IntPtr database);
        }

        private static class Mac
        {
            private const string Library = "/usr/lib/libsqlite3.dylib";

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern int sqlite3_open_v2(byte[] filename, out IntPtr database, int flags, IntPtr vfs);

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern int sqlite3_busy_timeout(IntPtr database, int milliseconds);

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern int sqlite3_exec(IntPtr database, byte[] sql, MacRowCallback callback, IntPtr context, out IntPtr error);

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern void sqlite3_free(IntPtr pointer);

            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, ExactSpelling = true)]
            internal static extern int sqlite3_close_v2(IntPtr database);
        }

        public NativeSqlite(string path, bool create, bool useWindows)
        {
            windows = useWindows;
            byte[] filename = Utf8(path);
            int flags = OpenReadWrite | (create ? OpenCreate : 0);
            try
            {
                int result = windows
                    ? Windows.sqlite3_open_v2(filename, out database, flags, IntPtr.Zero)
                    : Mac.sqlite3_open_v2(filename, out database, flags, IntPtr.Zero);
                Check(result, "open");
                Check(windows
                    ? Windows.sqlite3_busy_timeout(database, 10000)
                    : Mac.sqlite3_busy_timeout(database, 10000), "busy timeout");
            }
            catch
            {
                Dispose();
                throw;
            }
        }

        private static byte[] Utf8(string text)
        {
            if (text == null || text.IndexOf('\0') >= 0)
                throw new InvalidOperationException("Invalid native SQLite input.");
            return new UTF8Encoding(false, true).GetBytes(text + "\0");
        }

        private static void Check(int result, string operation)
        {
            // Native error strings may contain paths or SQL; expose only the numeric result.
            if (result != 0)
                throw new InvalidOperationException("SQLite " + operation + " failed (code " +
                    result.ToString(CultureInfo.InvariantCulture) + ").");
        }

        private static string SafeField(IntPtr pointer)
        {
            if (pointer == IntPtr.Zero)
                return String.Empty;
            StringBuilder field = new StringBuilder();
            for (int index = 0; index < 4096; index++)
            {
                byte value = Marshal.ReadByte(pointer, index);
                if (value == 0)
                    return field.ToString();
                if (!((value >= 'a' && value <= 'z') ||
                      (value >= 'A' && value <= 'Z') ||
                      (value >= '0' && value <= '9') ||
                      value == '_' || value == '-' || value == '.' || value == ':'))
                    throw new InvalidOperationException("Unsafe SQLite output.");
                field.Append((char)value);
            }
            throw new InvalidOperationException("Oversized SQLite output.");
        }

        public string[] Execute(string sql)
        {
            if (database == IntPtr.Zero)
                throw new ObjectDisposedException("NativeSqlite");
            List<string> rows = new List<string>();
            bool callbackFailed = false;
            Func<IntPtr, int, IntPtr, IntPtr, int> collect = delegate(IntPtr context, int count, IntPtr values, IntPtr names)
            {
                try
                {
                    if (count < 1 || count > 64)
                        throw new InvalidOperationException("Invalid SQLite output.");
                    string[] fields = new string[count];
                    for (int index = 0; index < count; index++)
                        fields[index] = SafeField(Marshal.ReadIntPtr(values, index * IntPtr.Size));
                    rows.Add(String.Join("|", fields));
                    return 0;
                }
                catch
                {
                    // Exceptions must not cross the unmanaged callback boundary.
                    callbackFailed = true;
                    return 1;
                }
            };
            WindowsRowCallback windowsCallback = windows ? new WindowsRowCallback(collect.Invoke) : null;
            MacRowCallback macCallback = windows ? null : new MacRowCallback(collect.Invoke);
            IntPtr error = IntPtr.Zero;
            try
            {
                byte[] statement = Utf8(sql);
                int result = windows
                    ? Windows.sqlite3_exec(database, statement, windowsCallback, IntPtr.Zero, out error)
                    : Mac.sqlite3_exec(database, statement, macCallback, IntPtr.Zero, out error);
                if (callbackFailed)
                    throw new InvalidOperationException("SQLite returned unsafe output.");
                Check(result, "execution");
                return rows.ToArray();
            }
            finally
            {
                if (error != IntPtr.Zero)
                {
                    if (windows) Windows.sqlite3_free(error);
                    else Mac.sqlite3_free(error);
                }
                GC.KeepAlive(windowsCallback);
                GC.KeepAlive(macCallback);
            }
        }

        public void Dispose()
        {
            if (database == IntPtr.Zero)
                return;
            IntPtr handle = database;
            database = IntPtr.Zero;
            Check(windows ? Windows.sqlite3_close_v2(handle) : Mac.sqlite3_close_v2(handle), "close");
        }
    }
}
