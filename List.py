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
        def __init__(self, sequence_number, active = True, conditional = False, condition = "", hit_times = 0):
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
        
        try:
            for i in range(total_lines):
                line = lines[i]


                match = re.match(pattern, line)
                if match:
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


                    new_breakpoint = self.BreakpointState(breakpoint_number,active,cond, condition, hit_times)

                    if line_number in breakpoints:
                        replacement =  (not cond and active ) or ( not cond and not active and breakpoints[line_number].conditional and not breakpoints[line_number].active ) or (cond and active and not breakpoints[line_number].active)

                        if replacement or breakpoints[line_number] == new_breakpoint:
                        
                            breakpoints[line_number] = new_breakpoint

                    else:
                        breakpoints[line_number]=new_breakpoint
        
        except Exception as e:
            print(f"Error: {e}")

        return breakpoints

    def getfilename(self):
        
        try:
            cmd = "i source"
            output = gdb.execute(cmd, to_string = True)
            line = output.splitlines()[0].rstrip()

            if line != "No current source file.":
                filename = output.splitlines()[0].rstrip().split(' ')[-1]
                return filename
            else:
                raise RuntimeError("No current source file.")
        except Exception as e:
            return ""


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

                #return

                sal = frame.find_sal()
                if sal and sal.symtab:

                    filename = sal.symtab.filename
                    next_line = sal.line
                #else:
                #    filename = self.getfilename()
                #    next_line = None
        except:
            filename = self.getfilename()
            next_line = None

        try:
            # Read the source file
            with open(filename, "r") as source_file:
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

            breakpoints = self.get_breakpoints(filename)
            length_breakpoints = self.max_digits_in_dict(breakpoints)

            leading_spaces = self.repeated_space(length_breakpoints)


            # Display lines with annotations and color
            for i in range(start_line, end_line + 1):
                suffix = ""

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

                elif next_line is not None and i == next_line:
                    prefix = f"{GREEN}{leading_spaces}  —▸"  # Mark next line to execute
                else:
                    prefix = f"{RESET}{leading_spaces}    "

                print(f"{prefix}{i:4}: {lines[i - 1].rstrip()}{suffix}{RESET}")

        except Exception as e:
            print(f"Error: {e}")

# Register the new list command
EnhancedListCommand()
