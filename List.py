import gdb

import traceback

def print_line_number():
    print(f"Current line number: {traceback.extract_stack()[-2].lineno}")


class EnhancedListCommand(gdb.Command):
    """
    Replaces the original `list` command to show source code with
    highlighted breakpoints (red) and the next line to be executed (green).
    """
    def __init__(self):
        super(EnhancedListCommand, self).__init__("List", gdb.COMMAND_FILES)
        gdb.execute("alias L = List")


    def max_digits_in_dict(self, breakpoints):
        # Get all the numbers from the dictionary

        max_length = 0

        for value in breakpoints.values():
            new_length = len(str(value.sequence_number))
            if new_length > max_length:
                max_length = new_length


        return max_length

    class BreakpointState:
        def __init__(self, line_number, sequence_number, active = True, conditional = False, condition = "", hit_times = 0):

            self.line_number = line_number
            self.conditional = conditional
            self.active = active
            self.sequence_number = sequence_number
            self.condition = condition
            self.hit_times = hit_times


        def __eq__(self, other):
            if isinstance(other, EnhancedListCommand.BreakpointState):
                return self.conditional == other.conditional and self. active==other.active
            return False

        def get_condition(self):
            return self.condition

        def get_hit_times(self):
            return self.hit_times

        def show(self):
            print(f"condifional: {self.conditional}\nactive: {self.active}\nbreak number: {self.sequence_number}\n")

    def get_hit_times(self, line):

        hit_times = 0
        pattern = r"^\s*breakpoint already hit\s+(\d+)\s+time.*$"
        match = re.match(pattern, line)
        if match:
            hit_times=int(match.group(1))

        return hit_times

    def filter_condition(self, breakpointer_state, line_number, active, conditional):
        return breakpointer_state.line_number == line_number and breakpointer_state.active == active and breakpointer_state.conditional == conditional

    def get_all_line_numbers(self, breakpoints):
        ordered_set = {}

        # Add elements

        for breakpoint in breakpoints:
            ordered_set[breakpoint.line_number] = None

        # Convert keys to a list if needed
        result = list(ordered_set.keys())

        return result  # Output: [1, 2, 3]



    def separate(self, all_breakpoints, breakpoints):


        breakpoint_dict={}


        for breakpoint in all_breakpoints:
            break_info = [breakpoint.sequence_number, breakpoint.active, breakpoint.conditional, breakpoint.condition, breakpoint.hit_times]

            if breakpoint.line_number not in breakpoint_dict or breakpoint_dict[breakpoint.line_number] is None:
                breakpoint_dict[breakpoint.line_number] =[]

            breakpoint_dict[breakpoint.line_number].append(break_info)

        sorted_breakpoint_dict ={}

        for key, value in breakpoint_dict.items():

            left_value = []

            for row in value:
                if row[0] != breakpoints[key].sequence_number:
                    left_value.append(row)

            sorted_breakpoint = sorted(left_value, key=lambda x: (not x[1], x[0]))
            sorted_breakpoint_dict[key]=sorted_breakpoint

        return sorted_breakpoint_dict

    def get_breakpoints(self, filename):
        """
        The breakpoints returned from gdb.breakpoints() are not correct
        If breakpoints are set multiple times at the same line, if anyone of them is active, then the breakpoint is active.
        If the breakpoint is actibe or inactive, the corresponding breakpoint sequence number always shows the one that set the latest.
        """

        cmd = "i b"
        output = gdb.execute(cmd, to_string = True)
        lines = output.splitlines()

        breakpoints={}

        pattern = rf"^\s*(\d+).*\s+keep\s+([yn])\s+.*{filename}:(\d+)\s*$"
        pattern_cond = r"^\s*(stop only if.*)$"     # conditioanl breakpoint
        total_lines = len(lines)

        all_breakpoints = []

        try:
            for i in range(total_lines):
                line = lines[i]

                matched = False

                line_number = -1
                breakpoint_number = -1
                active = None
                cond = None
                condition = ""
                hit_times = 0


                match = re.match(pattern, line)
                if match:
                    matched = True
                    breakpoint_number=int(match.group(1))
                    active = match.group(2) == 'y'
                    line_number = int(match.group(3))

                    cond = False
                    condition = ""
                    hit_times = 0

                    if i < total_lines-1:

                        next_line = lines[i+1]

                        match = re.match(pattern_cond, next_line)
                        if match:

                            cond = True
                            condition = match.group(1)

                            if i < total_lines-2:
                                hit_times = self.get_hit_times(lines[i+2])
                        else:
                            hit_times = self.get_hit_times(lines[i+1])


                    new_breakpoint = self.BreakpointState(line_number,breakpoint_number, active,cond, condition, hit_times)
                    all_breakpoints.append(new_breakpoint)
                else:
                    pattern = rf"^\s*(\d+).*\s+keep\s+([yn])\s+.*{filename}:(\d+)\s*$"
                    pattern_cond = r"^\s*(stop only if.*)$"     # conditioanl breakpoint
                    pattern_sub_mult = rf"^\s*(\d+\.\d+)\s+([yn])\s+.*\s+at\s+{filename}:(\d+)\s*$"
                    pattern_mult = r"\s*(\d+)\s+breakpoint\s+keep\s+(\S)\s+<MULTIPLE>.*$"

                    match = re.match(pattern_mult, line)
                    if match:
                        matched = True
                        breakpoint_number=int(match.group(1))

                        active = match.group(2) == 'y'
                        cond = False
                        condition = ""

                        if i < total_lines -2:
                            line = lines[i+1]
                            match = re.match(pattern_cond, line)

                            if match:
                                cond = True
                                condition = match.group(1)
                                j = i + 2
                            else:
                                j = i+1

                        if j < total_lines -1:
                            line = lines[j]
                            match = re.match(pattern_sub_mult, line)

                            if match:
                                line_number = int(match.group(3))


                if matched:

                    new_breakpoint = self.BreakpointState(line_number,breakpoint_number, active,cond, condition, hit_times)
                    all_breakpoints.append(new_breakpoint)

                    if line_number in breakpoints:
                        replacement =  (not cond and active ) or ( not cond and not active and breakpoints[line_number].conditional and not breakpoints[line_number].active ) or (cond and active and not breakpoints[line_number].active)

                        if replacement or breakpoints[line_number] == new_breakpoint:

                            breakpoints[line_number] = new_breakpoint

                    else:
                        breakpoints[line_number]=new_breakpoint




        except Exception as e:
            print(f"Error: {e}")

        sorted_breakpoint_dict = self.separate(all_breakpoints, breakpoints)

        return breakpoints, sorted_breakpoint_dict # breakpoints is a list of classes. sorted_breakpoint_dict is a dict of list


    def getfilename(self):

        try:
            cmd = "i source"
            output = gdb.execute(cmd, to_string = True)
            lines = output.splitlines()
            line = lines[0].rstrip()

            if line != "No current source file.":
                filename = lines[0].rstrip().split(' ')[-1]
                line = lines[2].rstrip()
                pattern = r"^\s*Located in\s+(\S+.*)$"
                match = re.match(pattern, line)
                if match:
                    path=match.group(1)

                return filename, path
            else:
                raise RuntimeError("No current source file.")

        except Exception as e:
            return "", ""


    def getscope(self, argument):
        cmd = "list " + argument
        output = gdb.execute(cmd, to_string = True)
        lines = output.splitlines()
        first_line = lines[0]
        last_line = lines[-1]
        #line_number_pattern = re.compile(r"^(\d+):\s*")

        first_line_number = None
        last_line_number = None

        match = re.match(r'^\s*(\d+)\s', first_line)
        if match:
            first_line_number = match.group(1)

        match = re.search(r'^\s*(\d+)\s', last_line)
        if match:
            last_line_number = match.group(1)

        return int(first_line_number), int(last_line_number)

    def repeated_space(self, length):
        return ''.join(" " for _ in range(length))

    def compose_breakpoint_prefix(self, i, maxlen):
        return self.repeated_space(maxlen-len(str(i))) + str(i)

    def len_no_ansi(self, string):
        return len(re.sub(
        r'[\u001B\u009B][\[\]()#;?]*((([a-zA-Z\d]*(;[-a-zA-Z\d\/#&.:=?%@~_]*)*)?\u0007)|((\d{1,4}(?:;\d{0,4})*)?[\dA-PR-TZcf-ntqry=><~]))', '', string))


    def invoke(self, arg, from_tty):
        #try:
        # ANSI color codes
        RED = "\033[31m"
        DARKRED= "\033[35m"
        GREEN = "\033[32m"
        RESET = "\033[0m"
        YELLOW = "\033[33m"

        # Determine the current frame

        try:
            frame = gdb.selected_frame()
            if frame:

                sal = frame.find_sal()
                if sal and sal.symtab:

                    filename = sal.symtab.filename
                    path= sal.symtab.fullname()
                    next_line = sal.line
        except:
            filename, path = self.getfilename()
            next_line = None

        try:
            # Read the source file
            with open(path, "r") as source_file:
                lines = source_file.readlines()
        except Exception as e:
            print("Error: No current source file.")
            return

        try:
            start_line, end_line = self.getscope(arg)

            # Get all breakpoints
            """
            breakpoints = gdb.breakpoints() or []
            bp_lines = {int(bp.location.split(":")[-1]) for bp in breakpoints if ":" in bp.location}
            """

            breakpoints, breakpoint_dict = self.get_breakpoints(filename)


            length_breakpoints = self.max_digits_in_dict(breakpoints)

            leading_spaces = self.repeated_space(length_breakpoints)


            # Display lines with annotations and color
            for i in range(start_line, end_line + 1):
                suffix = ""
                other_breakpoints_message = ""

                if i in breakpoints:

                    if breakpoints[i].active:
                        line_color = RED
                        prefix = "●"  # Mark breakpoint lines
                    else:
                        line_color = DARKRED
                        prefix = "○"  # Mark breakpoint lines

                    prefix= f"{RED}{prefix}"

                    if breakpoints[i].conditional:
                        prefix+='?'
                    else:
                        prefix+=' '

                    prefix += f"{line_color}"

                    if next_line is not None and i == next_line:
                        prefix += f"{GREEN}—▸{line_color}"  # Mark next line to execute
                    else:
                        prefix += "  "  # Mark next line to execute

                    break_point_prefix = self.compose_breakpoint_prefix(breakpoints[i].sequence_number, length_breakpoints)
                    prefix = f"{RESET}{break_point_prefix}{prefix}"

                    if breakpoints[i].conditional:
                        suffix = f"\t{YELLOW}({breakpoints[i].get_condition()})"

                    if breakpoints[i].hit_times > 0:
                        times = breakpoints[i].get_hit_times()
                        message = "(" + "hit " + str(times) + " time" + ("" if times == 1 else "s") + ")"
                        suffix += f"\t{YELLOW}{message}"

                    cursor_position = self.len_no_ansi(f"{prefix}{i:4}: {lines[i - 1].rstrip()}")
                    spaces = " " * cursor_position

                    all_breakpoints_in_the_line = breakpoint_dict[i]


                    for row in all_breakpoints_in_the_line:
                        if row[-1] > 0:
                            hit_times ="(" + "hit " + str(row[-1]) + " time" + ("" if row[-1] == 1 else "s") + ")"
                        else:
                            hit_times = ""

                        maxlen = len(str(max(all_breakpoints_in_the_line, key=lambda x: len(str(x[0])))[0]))
                        other_leading_spaces = self.repeated_space(maxlen-len(str(row[0])))

                        message = "("+ RED + other_leading_spaces + RESET + str(row[0])+ RED + ( '●' if row[1] else '○' ) +( '?' if row[2] else '' )+YELLOW+ (("  "+ row[3]) if row[3]!= "" else "" ) +")\t"+ hit_times

                        message = f"{spaces}\t{YELLOW}{message}{RESET}"
                        other_breakpoints_message +=( message + "\n" )


                elif next_line is not None and i == next_line:
                    prefix = f"{GREEN}{leading_spaces}  —▸"  # Mark next line to execute
                else:
                    prefix = f"{RESET}{leading_spaces}    "

                print(f"{prefix}{i:4}: {lines[i - 1].rstrip()}{suffix}{RESET}")
                if other_breakpoints_message != "":
                    print(other_breakpoints_message.rstrip())


        except Exception as e:
            print(f"Error: {e}")

# Register the new list command
EnhancedListCommand()
