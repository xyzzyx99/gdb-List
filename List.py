import gdb

class EnhancedListCommand(gdb.Command):
    """
    Replaces the original `list` command to show source code with
    highlighted breakpoints (red) and the next line to be executed (green).
    """
    def __init__(self):
        super(EnhancedListCommand, self).__init__("List", gdb.COMMAND_FILES)
        gdb.execute("alias L = List")

    #def getscope(self, arg, from_tty):
    def getscope(self, argument):
        cmd = "list " + argument
        output = gdb.execute(cmd, to_string = True)
        #print(output)
        lines = output.splitlines()
        first_line = lines[0]
        last_line = lines[-1]
        line_number_pattern = re.compile(r"^(\d+):\s*")
       
        #print(first_line)
        #print(last_line)
        
        first_line_number = None
        last_line_number = None

        match = re.match(r'^\s*(\d+)\s', first_line)
        if match:
            first_line_number = match.group(1)
            
        match = re.search(r'^\s*(\d+)\s', last_line)
        if match:
            last_line_number = match.group(1)
        
        #last_line_number = match.group(0) for match in line_number_pattern.finditer(last_line)

        return int(first_line_number), int(last_line_number) 

    def invoke(self, arg, from_tty):
        try:
            # ANSI color codes
            RED = "\033[31m"
            GREEN = "\033[32m"
            RESET = "\033[0m"

            # Determine the current frame
            frame = gdb.selected_frame()
            if not frame:
                print("No frame selected.")
                return

            sal = frame.find_sal()
            if not sal or not sal.symtab:
                print("No source information available.")
                return

            filename = sal.symtab.filename
            next_line = sal.line

            # Read the source file
            with open(filename, "r") as source_file:
                lines = source_file.readlines()

            # Determine the range of lines to display (default: 10 lines)
            #start_line = max(next_line - 5, 1)
            #end_line = min(next_line + 4, len(lines))

            start_line, end_line = self.getscope(arg)

            # Get all breakpoints
            breakpoints = gdb.breakpoints() or []
            bp_lines = {int(bp.location.split(":")[-1]) for bp in breakpoints if ":" in bp.location}
            #print(bp_lines)

            prefix = ""

            # Display lines with annotations and color
            for i in range(start_line, end_line + 1):
#                prefix = "   "
#                line_color = RESET  # Default color

                if i in bp_lines:
                    line_color = RED
                    prefix = "●"  # Mark breakpoint lines
                    prefix= f"{RED}{prefix}"
                    if i == next_line:
                        prefix += f"{GREEN} —▸{RED}"  # Mark next line to execute
                        #line_color = GREEN
                    else:
                        prefix += "   "  # Mark next line to execute
                elif i == next_line:
                    prefix = f"{GREEN}  —▸"  # Mark next line to execute
                    #line_color = GREEN
                else:
                    prefix = f"{RESET}    "
                    #line_color = RESET  # Default color

                #print(f"{line_color}{prefix}{i:4}: {lines[i - 1].rstrip()}{RESET}")
                print(f"{prefix}{i:4}: {lines[i - 1].rstrip()}{RESET}")

        except Exception as e:
            print(f"Error: {e}")

# Register the new list command
EnhancedListCommand()
