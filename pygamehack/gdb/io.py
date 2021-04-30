import re
import io
import time

from .parser import parse_response, response_is_finished

#region GDBIO

class GDBIO(object):

    #region Public

    def __init__(self, stdin, stdout, stderr):
        self.time_to_check_for_additional_output_sec = 0.2
        self.allow_overwrite_timeout_times = self.time_to_check_for_additional_output_sec > 0
        
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        self.stdin_fileno = self.stdin.fileno()
        self.stdout_fileno = self.stdout.fileno()
        self.stderr_fileno = self.stderr.fileno() if self.stderr else -1
        self.read_list = [self.stdout_fileno]
        self.write_list = [self.stdin_fileno]

        self.incomplete_output = {"stdout": None, "stderr": None}

        _make_non_blocking(self.stdout)
        if self.stderr:
            _make_non_blocking(self.stderr)

    def read(self, done_handler, timeout_sec = 1.0):
        """Get a list of responses from GDB, and block while doing so.

        Args:
            timeout_sec: Maximum time to wait for reponse. Must be >= 0. Will return after

        Returns:
            List of parsed GDB responses, returned from gdbmiparser.parse_response, with the
            additional key 'stream' which is either 'stdout' or 'stderr'
        """
        assert timeout_sec >= 0
        done_handler = done_handler or (lambda r: False)
        return self._get_responses_windows(timeout_sec, done_handler) if _USING_WINDOWS \
            else self._get_responses_unix(timeout_sec, done_handler)

    def write(self, data):
        """Write to gdb process. Block while parsing responses from gdb for a maximum of timeout_sec.

        Args:
            data: String to write to gdb. 
        """

        if not data.endswith("\n"):
            mi_cmd_to_write_nl = data + "\n"
        else:
            mi_cmd_to_write_nl = data

        if _USING_WINDOWS:
            # select not implemented in windows for pipes
            # assume it's always ready
            outputready = [self.stdin_fileno]
        else:
            _, outputready, _ = select.select([], self.write_list, [], timeout_sec)
        for fileno in outputready:
            if fileno == self.stdin_fileno:
                # ready to write
                self.stdin.write(mi_cmd_to_write_nl.encode())
                # must flush, otherwise gdb won't realize there is data
                # to evaluate, and we won't get a response
                self.stdin.flush() 
            else:
                raise RuntimeError("got unexpected fileno %d" % fileno)

    #endregion

    #region Private

    def _get_responses_windows(self, timeout_sec, handler):
        """Get responses on windows. Assume no support for select and use a while loop."""
        timeout_time_sec = time.time() + timeout_sec
        responses = []
        while True:
            responses_list = []
            try:
                self.stdout.flush()
                raw_output = self.stdout.readline().replace(b"\r", b"\n")
                responses_list = self._get_responses_list(raw_output, "stdout")
            except IOError:
                pass

            try:
                self.stderr.flush()
                raw_output = self.stderr.readline().replace(b"\r", b"\n")
                responses_list += self._get_responses_list(raw_output, "stderr")
            except IOError:
                pass

            responses += responses_list
            
            if handler(responses_list):
                break
            elif timeout_sec == 0:
                break
            elif responses_list and self.allow_overwrite_timeout_times:
                timeout_time_sec = min(
                    time.time() + self.time_to_check_for_additional_output_sec,
                    timeout_time_sec,
                )
            elif time.time() > timeout_time_sec:
                break

        return responses

    def _get_responses_unix(self, timeout_sec, handler):
        """Get responses on unix-like system. Use select to wait for output."""
        timeout_time_sec = time.time() + timeout_sec
        responses = []
        while True:
            select_timeout = timeout_time_sec - time.time()
            if select_timeout <= 0:
                select_timeout = 0
            events, _, _ = select.select(self.read_list, [], [], select_timeout)
            responses_list = None  # to avoid infinite loop if using Python 2
            for fileno in events:
                # new data is ready to read
                if fileno == self.stdout_fileno:
                    self.stdout.flush()
                    raw_output = self.stdout.read()
                    stream = "stdout"

                elif fileno == self.stderr_fileno:
                    self.stderr.flush()
                    raw_output = self.stderr.read()
                    stream = "stderr"

                else:
                    raise ValueError(
                        "Developer error. Got unexpected file number %d" % fileno
                    )
                responses_list = self._get_responses_list(raw_output, stream)
                responses += responses_list

            if handler(responses_list):
                break

            elif timeout_sec == 0:  # just exit immediately
                break

            elif responses_list and self.allow_overwrite_timeout_times:
                # update timeout time to potentially be closer to now to avoid lengthy wait times when nothing is being output by gdb
                timeout_time_sec = min(
                    time.time() + self.time_to_check_for_additional_output_sec,
                    timeout_time_sec,
                )

            elif time.time() > timeout_time_sec:
                break

        return responses

    def _get_responses_list(self, raw_output: bytes, stream: str):
        """Get parsed response list from string output
        Args:
            raw_output (unicode): gdb output to parse
            stream (str): either stdout or stderr
        """
        responses = []

        (_new_output, self.incomplete_output[stream],) = _buffer_incomplete_responses(
            raw_output, self.incomplete_output.get(stream)
        )

        if not _new_output:
            return responses

        response_list = list(
            filter(lambda x: x, _new_output.decode(errors="replace").split("\n"))
        )  # remove blank lines

        # parse each response from gdb into a dict, and store in a list
        for response in response_list:
            if response_is_finished(response):
                pass
            else:
                parsed_response = parse_response(response)
                # parsed_response["stream"] = stream

                # logger.debug("%s", pformat(parsed_response))

                responses.append(parsed_response)

        return responses

    #endregion

#endregion

#region GDBIO Helpers

_USING_WINDOWS = True

def _buffer_incomplete_responses(raw_output, buf):
    """It is possible for some of gdb's output to be read before it completely finished its response.
    In that case, a partial mi response was read, which cannot be parsed into structured data.
    We want to ALWAYS parse complete mi records. To do this, we store a buffer of gdb's
    output if the output did not end in a newline.

    Args:
        raw_output: Contents of the gdb mi output
        buf (str): Buffered gdb response from the past. This is incomplete and needs to be prepended to
        gdb's next output.

    Returns:
        (raw_output, buf)
    """

    if raw_output:
        if buf:
            # concatenate buffer and new output
            raw_output = b"".join([buf, raw_output])
            buf = None

        if b"\n" not in raw_output:
            # newline was not found, so assume output is incomplete and store in buffer
            buf = raw_output
            raw_output = None

        elif not raw_output.endswith(b"\n"):
            # raw output doesn't end in a newline, so store everything after the last newline (if anything)
            # in the buffer, and parse everything before it
            remainder_offset = raw_output.rindex(b"\n") + 1
            buf = raw_output[remainder_offset:]
            raw_output = raw_output[:remainder_offset]

    return (raw_output, buf)


def _make_non_blocking(file_obj):
    """make file object non-blocking
    Windows doesn't have the fcntl module, but someone on
    stack overflow supplied this code as an answer, and it works
    http://stackoverflow.com/a/34504971/2893090"""
    if _USING_WINDOWS:
        import msvcrt
        from ctypes import windll, byref, wintypes, WinError, POINTER
        from ctypes.wintypes import HANDLE, DWORD, BOOL

        LPDWORD = POINTER(DWORD)
        PIPE_NOWAIT = wintypes.DWORD(0x00000001)

        SetNamedPipeHandleState = windll.kernel32.SetNamedPipeHandleState
        SetNamedPipeHandleState.argtypes = [HANDLE, LPDWORD, LPDWORD, LPDWORD]
        SetNamedPipeHandleState.restype = BOOL

        h = msvcrt.get_osfhandle(file_obj.fileno())

        res = windll.kernel32.SetNamedPipeHandleState(h, byref(PIPE_NOWAIT), None, None)
        if res == 0:
            raise ValueError(WinError())

    else:
        import fcntl
        # Set the file status flag (F_SETFL) on the pipes to be non-blocking
        # so we can attempt to read from a pipe with no new data without locking
        # the program up
        fcntl.fcntl(file_obj, fcntl.F_SETFL, os.O_NONBLOCK)


#endregion
