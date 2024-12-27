import gdb

class EnhancedListCommand(gdb.Command):
    """
    Replaces the original `list` command to show source code with
    highlighted breakpoints (red) and the next line to be executed (green).
    """
    def __init__(self):
        super(EnhancedListCommand, self).__init__("List", gdb.COMMAND_FILES)
        gdb.execute("alias L = List")


    def max_digits_in_dict(self, numbers_dict):
        # Get all the numbers from the dictionary
        values = numbers_dict.values()

        if len(numbers_dict) == 0:
            values = [0]

        # Find the maximum number of digits
        #try:
        max_digits = max(len(str(abs(int(v)))) for v in values)
        #except:
        #    max_digits = 0
        
        return max_digits


    def get_breakpoints(self, filename):
        """
        The breakpoints returned from gdb.breakpoints() are not correct
        """
        cmd = "i b"
        output = gdb.execute(cmd, to_string = True)
        lines = output.splitlines()
        
        breakpoints = {}
        breakpoints_number={}

        pattern = rf"^\s*(\d+).*\s+keep\s+([yn])\s+.*{filename}:(\d+)\s*$"
        for line in lines:
            match = re.match(pattern, line)
            if match:
                breakpoint_number=match.group(1)
                active = match.group(2)
                line_number = match.group(3)
                breakpoints[int(line_number)] = active
                breakpoints_number[int(line_number)] = breakpoint_number
        
        return breakpoints, breakpoints_number

    def getfilename(self):
        
        try:
            cmd = "i source"
            output = gdb.execute(cmd, to_string = True)
            filename = output.splitlines()[0].rstrip().split(' ')[-1]
            return filename
        except Exception as e:
            print(f"Error: {e}")


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

        # Determine the current frame
       
        try:
            frame = gdb.selected_frame()
            if frame:

                #print("No frame selected.")
                #return

                sal = frame.find_sal()
                if sal and sal.symtab:
                    #print("No source information available.")
                    #return

                    filename = sal.symtab.filename
                    next_line = sal.line
                #else:
                #    filename = self.getfilename()
                #    next_line = None
        except:
        #else:
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
            #print(bp_lines)
            """

            breakpoints, breakpoints_number = self.get_breakpoints(filename)
            length_breakpoints = self.max_digits_in_dict(breakpoints_number)

            leading_spaces = self.repeated_space(length_breakpoints)

            # Display lines with annotations and color
            for i in range(start_line, end_line + 1):

                if i in breakpoints:
                   # line_color = RED

                    if breakpoints[i] == 'y':
                        line_color = RED
                        prefix = "●"  # Mark breakpoint lines
                    else:
                        line_color = DARKRED
                        prefix = "○"  # Mark breakpoint lines

                    prefix= f"{RED}{prefix}{line_color}"
                    if next_line is not None and i == next_line:
                        prefix += f"{GREEN} —▸{line_color}"  # Mark next line to execute
                        #line_color = GREEN
                    else:
                        prefix += "   "  # Mark next line to execute
                    
                    break_point_prefix = self.compose_breakpoint_prefix(breakpoints_number[i], length_breakpoints)
                    prefix = f"{RESET}{break_point_prefix}{prefix}"

                elif next_line is not None and i == next_line:
                    prefix = f"{GREEN}{leading_spaces}  —▸"  # Mark next line to execute
                    #line_color = GREEN
                else:
                    prefix = f"{RESET}{leading_spaces}    "
                    #line_color = RESET  # Default color

                #print(f"{line_color}{prefix}{i:4}: {lines[i - 1].rstrip()}{RESET}")
                print(f"{prefix}{i:4}: {lines[i - 1].rstrip()}{RESET}")

        except Exception as e:
            #print("Error: No current source file.")
            print(f"Error: {e}")

# Register the new list command
EnhancedListCommand()
