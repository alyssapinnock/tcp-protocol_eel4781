"""
Name: Alyssa Pinnock
Course: EEL 4781 - Computer Communication Networks
Project: Programming Project - Option C (TCP-Like Protocol)
Description: Main UI file (using Pygame)
"""

import pygame
import sys
from channel import Channel
from sender import Sender
from receiver import Receiver

# -------------------------------------------------
# Global constants & colors
# -------------------------------------------------
screenWidth = 1200
screenHeight = 800

# colors
white = (255, 255, 255)
black = (0, 0, 0)
gray = (200, 200, 200)
blue = (50, 100, 255)       
red = (255, 50, 50)         
yellow = (255, 200, 0)      
green = (50, 200, 50)
orange = (255, 165, 0)
lightGray = (240, 240, 240)
darkGray = (100, 100, 100)

# -------------------------------------------------
# UI helper classes
# -------------------------------------------------

class InputBox:
    def __init__(self, x, y, w, h, text='', label=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = black
        self.text = text
        self.label = label
        self.font = pygame.font.SysFont("Arial", 18)
        self.txt_surface = self.font.render(text, True, self.color)
        self.active = False

    def handle_event(self, event):
        updated = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            # toggle active state if clicked inside
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = blue if self.active else black
            
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.active = False
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                    updated = True
                else:
                    # we only want numbers here
                    if event.unicode.isdigit():
                        self.text += event.unicode
                        updated = True
                self.txt_surface = self.font.render(self.text, True, self.color)
        return updated

    def draw(self, screen):
        # put the label a bit above the box
        label_surf = pygame.font.SysFont("Arial", 16).render(self.label, True, darkGray)
        screen.blit(label_surf, (self.rect.x, self.rect.y - 20))
        
        pygame.draw.rect(screen, self.color, self.rect, 2)
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))

    def get_value(self):
        try:
            return int(self.text)
        except ValueError:
            return 0
    
    def set_value(self, val):
        self.text = str(val)
        self.txt_surface = self.font.render(self.text, True, self.color)

class Button:
    def __init__(self, x, y, w, h, text, color, action_code, font_size=16):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.action_code = action_code
        self.font = pygame.font.SysFont("Arial", font_size, bold=True)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        draw_rect = self.rect
        
        # make the button pop out if hovered (unless it's disabled/gray)
        if self.rect.collidepoint(mouse_pos) and self.color != gray:
            draw_rect = self.rect.inflate(4, 4)
            
        pygame.draw.rect(screen, self.color, draw_rect)
        pygame.draw.rect(screen, black, draw_rect, 2)
        
        text_surf = self.font.render(self.text, True, black)
        text_rect = text_surf.get_rect(center=draw_rect.center)
        screen.blit(text_surf, text_rect)

# -------------------------------------------------
# Main Menu
# -------------------------------------------------

class NetworkSim:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((screenWidth, screenHeight))
        pygame.display.set_caption("TCP-Like Protocol Simulator (Option C)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 16)
        self.title_font = pygame.font.SysFont("Arial", 22, bold=True)
        
        self.state = 'MENU'
        self.channel = None
        self.sender = None
        self.receiver = None
        self.logs = [] 
        
        self.clickable_packets = [] 
        self.selected_packet = None 

        # sets to keep track of which boxes the user clicked in the menu
        self.config_loss_data = set() 
        self.config_loss_ack = set()  
        self.menu_box_rects = []      

        # default inputs
        self.inputs = [
            InputBox(100, 260, 100, 32, text='4', label='Window (N)'),
            InputBox(250, 260, 100, 32, text='10', label='Total Pkts (Max 15)'),
            InputBox(400, 260, 100, 32, text='120', label='Timeout (Ticks)'),
            InputBox(550, 260, 100, 32, text='60', label='Prop. Delay'),
        ]
        
        self.start_btn = Button(450, 720, 300, 50, "START SIMULATION", green, 'START', 20)
        
        # sim control buttons
        self.send_new_btn = Button(20, 680, 120, 40, "SEND NEW", blue, 'SEND_NEW')
        self.pause_btn    = Button(160, 680, 100, 40, "PAUSE", yellow, 'TOGGLE_PAUSE')
        self.kill_btn     = Button(280, 680, 160, 40, "KILL PACKET/ACK", red, 'KILL')
        
        self.reset_btn    = Button(460, 680, 80, 40, "RESET", lightGray, 'RESET')
        self.slower_btn   = Button(560, 680, 80, 40, "SLOWER", lightGray, 'SLOWER')
        self.faster_btn   = Button(660, 680, 80, 40, "FASTER", lightGray, 'FASTER')
        
        self.sim_buttons = [self.send_new_btn, self.pause_btn, self.kill_btn, 
                            self.reset_btn, self.slower_btn, self.faster_btn]
        
        self.paused = False
        # start slow so the user can see what's happening
        self.sim_speed = 15 

    def add_log(self, text, color=black):
        # keeps the on-screen log from getting too long
        self.logs.append((text, color))
        if len(self.logs) > 28: 
            self.logs.pop(0)
            
        # Print to terminal:
        print(text)

    def validate_config(self):
        # 1. Cap total packets at 15 to fit on screen
        total = self.inputs[1].get_value()
        
        if total > 15:
            total = 15
            self.inputs[1].set_value(15)
            
        # if the box is empty (0), use 1 for visuals so we don't crash
        visual_total = total
        if visual_total < 1:
            visual_total = 1

        # 2. Window size checks
        win = self.inputs[0].get_value()
        
        # window can't be bigger than the total amount of work
        if win > visual_total:
            win = visual_total
            self.inputs[0].set_value(win)
            
        visual_win = win
        if visual_win < 1:
            visual_win = 1
            
        return visual_win, visual_total

    def start_simulation(self):
        print("\n" + "="*40)
        print("--- SIMULATION STARTED ---")
        print("="*40)
        
        win_size, total_pkts = self.validate_config()
        
        # grab timeout/delay, using defaults if empty
        timeout = self.inputs[2].get_value()
        if timeout < 1: timeout = 100
        
        delay = self.inputs[3].get_value()
        if delay < 1: delay = 60
        
        loss_data_list = list(self.config_loss_data)
        loss_ack_list = list(self.config_loss_ack)

        # initialize the backend logic
        self.channel = Channel(loss_data_list, loss_ack_list, delay, log_callback=self.add_log)
        self.sender = Sender(self.channel, win_size, timeout, total_pkts, log_callback=self.add_log)
        self.receiver = Receiver(self.channel, log_callback=self.add_log)
        
        # link them up
        self.sender.set_receiver_ref(self.receiver)
        self.receiver.set_sender_ref(self.sender)
        
        self.logs = [] 
        self.selected_packet = None
        self.state = 'SIMULATION'
        self.paused = False

    def handle_menu_events(self, event):
        for box in self.inputs:
            updated = box.handle_event(event)
            # if user typed something, update the red/white boxes below
            if updated: self.validate_config()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.start_btn.is_clicked(event.pos):
                self.start_simulation()
            
            # handle clicking the visual configuration grid
            for rect, idx, type_str in self.menu_box_rects:
                if rect.collidepoint(event.pos):
                    if type_str == 'DATA':
                        # toggle data loss
                        if idx in self.config_loss_data:
                            self.config_loss_data.remove(idx)
                        else:
                            self.config_loss_data.add(idx)
                    else: 
                        # toggle ack loss
                        if idx in self.config_loss_ack:
                            self.config_loss_ack.remove(idx)
                        else:
                            self.config_loss_ack.add(idx)

    def handle_sim_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            for btn in self.sim_buttons:
                if btn.is_clicked(event.pos):
                    if btn.action_code == 'SEND_NEW':
                        # only allow sending if window isn't full (button not gray)
                        if self.send_new_btn.color != gray:
                            success = self.sender.attempt_send_one()
                            if not success: self.add_log("Window Full!", orange)
                    
                    if btn.action_code == 'TOGGLE_PAUSE': 
                        self.paused = not self.paused
                        self.selected_packet = None
                    
                    if btn.action_code == 'KILL':
                        # logic to remove a packet mid-flight
                        if self.paused and self.selected_packet:
                            success = self.channel.kill_specific_packet(self.selected_packet)
                            if success:
                                name = f"ACK {self.selected_packet.ackNum}" if self.selected_packet.isAck else f"Data {self.selected_packet.seqNum}"
                                self.add_log(f"KILLED {name} (User Click)", red)
                                self.selected_packet = None
                        elif not self.paused:
                            self.add_log("Must PAUSE to kill!", orange)
                        else:
                            self.add_log("Select a packet first!", orange)

                    if btn.action_code == 'RESET': 
                        print("\n--- SIMULATION RESET ---\n")
                        self.state = 'MENU'
                        
                    if btn.action_code == 'FASTER': self.sim_speed = min(120, self.sim_speed + 5)
                    if btn.action_code == 'SLOWER': self.sim_speed = max(5, self.sim_speed - 5)

            # selecting a packet on screen (turns green)
            if self.paused:
                clicked_any = False
                for rect, pkt_obj in self.clickable_packets:
                    if rect.collidepoint(event.pos):
                        self.selected_packet = pkt_obj
                        clicked_any = True
                        break
                # deselect if clicking void
                if not clicked_any and event.pos[1] < 680:
                    self.selected_packet = None

    # -------------------------------------------------
    # Drawing Functions
    # -------------------------------------------------

    def draw_menu(self):
        self.screen.fill(white)
        
        # header area
        title = self.title_font.render("TCP-Like Protocol Configuration", True, black)
        self.screen.blit(title, (screenWidth//2 - 160, 30))
        
        instr_lines = [
            "INSTRUCTIONS:",
            "1. Edit parameters below. Hover over boxes to type.",
            "2. VISUAL CONFIG: Click the boxes below to simulate automatic loss.",
            "   - Clicking a Sender Box (Top) drops that DATA packet.",
            "   - Clicking a Receiver Box (Bottom) drops that ACK packet.",
            "3. Press START. In simulation, use 'SEND NEW' to transmit packets.",
            "4. Pause & Click moving packets to kill them manually."
        ]
        y_txt = 70
        for line in instr_lines:
            txt = self.font.render(line, True, darkGray)
            self.screen.blit(txt, (100, y_txt))
            y_txt += 22

        # inputs and start button
        for box in self.inputs:
            box.draw(self.screen)
        
        self.start_btn.draw(self.screen)

        # visual grid for loss config
        win_size, total_pkts = self.validate_config()
        
        # 1. Sender row (Data Loss)
        y_start = 380
        lbl = self.title_font.render("SENDER PACKETS (DATA LOSS):", True, blue)
        self.screen.blit(lbl, (100, y_start - 30))
        
        # text summary of what is selected
        if self.config_loss_data:
            loss_str = ", ".join(str(x) for x in sorted(self.config_loss_data))
            txt_loss = self.font.render(f"Loss Data Packets: {loss_str}", True, red)
        else:
            txt_loss = self.font.render("Loss Data Packets: None", True, darkGray)
        self.screen.blit(txt_loss, (500, y_start - 30))

        self.menu_box_rects = []
        
        start_x = 100
        box_w = 40
        for i in range(total_pkts):
            x = start_x + (i * 50)
            rect = pygame.Rect(x, y_start, box_w, 40)
            is_lost = i in self.config_loss_data
            color = red if is_lost else white
            
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, black, rect, 2)
            
            num = self.font.render(str(i), True, black)
            self.screen.blit(num, (x+12, y_start+10))
            
            # preview window brackets for clarity
            if i == 0: 
                pygame.draw.line(self.screen, black, (x, y_start-5), (x, y_start+45), 3)
                pygame.draw.line(self.screen, black, (x, y_start-5), (x+10, y_start-5), 3)
                pygame.draw.line(self.screen, black, (x, y_start+45), (x+10, y_start+45), 3)
            if i == win_size - 1:
                pygame.draw.line(self.screen, black, (x+box_w, y_start-5), (x+box_w, y_start+45), 3)
                pygame.draw.line(self.screen, black, (x+box_w, y_start-5), (x+box_w-10, y_start-5), 3)
                pygame.draw.line(self.screen, black, (x+box_w, y_start+45), (x+box_w-10, y_start+45), 3)

            # draw 'X' if selected
            if is_lost:
                pygame.draw.line(self.screen, black, (x, y_start), (x+box_w, y_start+40), 3)
                pygame.draw.line(self.screen, black, (x, y_start+40), (x+box_w, y_start), 3)

            self.menu_box_rects.append((rect, i, 'DATA'))

        # 2. Receiver row (ACK Loss)
        y_start = 550
        lbl = self.title_font.render("RECEIVER PACKETS (ACK LOSS):", True, red)
        self.screen.blit(lbl, (100, y_start - 30))
        
        if self.config_loss_ack:
            loss_str = ", ".join(str(x) for x in sorted(self.config_loss_ack))
            txt_loss = self.font.render(f"Loss ACK Packets: {loss_str}", True, red)
        else:
            txt_loss = self.font.render("Loss ACK Packets: None", True, darkGray)
        self.screen.blit(txt_loss, (500, y_start - 30))
        
        for i in range(total_pkts):
            x = start_x + (i * 50)
            rect = pygame.Rect(x, y_start, box_w, 40)
            is_lost = i in self.config_loss_ack
            color = red if is_lost else white
            
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, black, rect, 2)
            
            num = self.font.render(str(i), True, black)
            self.screen.blit(num, (x+12, y_start+10))
            
            if is_lost:
                pygame.draw.line(self.screen, black, (x, y_start), (x+box_w, y_start+40), 3)
                pygame.draw.line(self.screen, black, (x, y_start+40), (x+box_w, y_start), 3)

            self.menu_box_rects.append((rect, i, 'ACK'))

    def draw_legend(self):
        y = 740
        legend_items = [
            ("Sent (Flight)", blue),
            ("Acknowledged", gray),
            ("ACK Packet", yellow),
            ("Selected", green),
            ("Buffered", orange)
        ]
        
        x = 20
        lbl = self.font.render("LEGEND: ", True, black)
        self.screen.blit(lbl, (x, y))
        x += 80
        
        for text, color in legend_items:
            pygame.draw.rect(self.screen, color, (x, y, 20, 20))
            pygame.draw.rect(self.screen, black, (x, y, 20, 20), 1)
            txt_surf = self.font.render(text, True, black)
            self.screen.blit(txt_surf, (x + 25, y))
            x += 140

    def draw_simulation(self):
        self.screen.fill(white)
        self.clickable_packets = [] 
        
        # --- Update buttons based on state ---
        if self.paused:
            self.pause_btn.text = "RESUME"
            self.pause_btn.color = green
            self.kill_btn.color = red 
        else:
            self.pause_btn.text = "PAUSE"
            self.pause_btn.color = yellow
            self.kill_btn.color = gray 

        # gray out sending if window is full
        if self.sender.is_window_full():
            self.send_new_btn.color = gray
        else:
            self.send_new_btn.color = blue

        # --- SENDER ---
        pygame.draw.line(self.screen, black, (0, 160), (750, 160), 1)
        lbl = self.title_font.render(f"SENDER (Window N={self.sender.windowSize})", True, blue)
        self.screen.blit(lbl, (20, 20))
        
        status_text = f"Base: {self.sender.base} | NextSeq: {self.sender.nextSeqNum} | Timer: {self.sender.timerCount}/{self.sender.timeoutInterval}"
        st_surf = self.font.render(status_text, True, black)
        self.screen.blit(st_surf, (20, 50))
        
        start_x = 50
        box_w = 40
        for i in range(self.sender.totalPackets):
            x = start_x + (i * 45)
            y = 80
            
            # determine color
            if i < self.sender.base:
                color = gray 
            elif i >= self.sender.base and i < self.sender.nextSeqNum:
                color = blue
            else:
                color = white
            
            pygame.draw.rect(self.screen, color, (x, y, box_w, 30))
            pygame.draw.rect(self.screen, black, (x, y, box_w, 30), 1)
            txt = self.font.render(str(i), True, black)
            self.screen.blit(txt, (x+12, y+5))
            
            # draw window brackets
            if i == self.sender.base:
                pygame.draw.line(self.screen, black, (x, y-10), (x, y+40), 3) 
                pygame.draw.line(self.screen, black, (x, y-10), (x+10, y-10), 3)
                pygame.draw.line(self.screen, black, (x, y+40), (x+10, y+40), 3)
            if i == self.sender.base + self.sender.windowSize - 1:
                pygame.draw.line(self.screen, black, (x+box_w, y-10), (x+box_w, y+40), 3) 
                pygame.draw.line(self.screen, black, (x+box_w, y-10), (x+box_w-10, y-10), 3)
                pygame.draw.line(self.screen, black, (x+box_w, y+40), (x+box_w-10, y+40), 3)

        # --- RECEIVER ---
        pygame.draw.line(self.screen, black, (0, 450), (750, 450), 1)
        lbl = self.title_font.render("RECEIVER", True, red)
        self.screen.blit(lbl, (20, 500))
        
        buf_list = list(self.receiver.buffer.keys())
        recv_status = f"Expected: {self.receiver.expectedSeqNum} | Buffered: {buf_list}"
        rst_surf = self.font.render(recv_status, True, black)
        self.screen.blit(rst_surf, (20, 530))
        
        for i in range(self.sender.totalPackets):
            x = start_x + (i * 45)
            y = 560
            color = white
            if i < self.receiver.expectedSeqNum: color = red
            elif i in self.receiver.buffer: color = orange
            
            pygame.draw.rect(self.screen, color, (x, y, box_w, 30))
            pygame.draw.rect(self.screen, black, (x, y, box_w, 30), 1)
            txt = self.font.render(str(i), True, black)
            self.screen.blit(txt, (x+12, y+5))
            
            if i == self.receiver.expectedSeqNum:
                pygame.draw.rect(self.screen, black, (x, y, box_w, 30), 3)

        # --- CHANNEL ---
        transit_start_y = 110
        transit_end_y = 560
        
        for item in self.channel.in_transit:
            pkt, ticks, _, total = item
            pct = 1.0 - (ticks / total)
            
            if pkt.isAck:
                curr_y = transit_end_y - ((transit_end_y - transit_start_y) * pct)
                color = yellow
                # align rising ack with the packet that triggered it
                visual_slot = max(0, pkt.ackNum - 1)
                x_pos = start_x + (visual_slot * 45)
            else:
                curr_y = transit_start_y + ((transit_end_y - transit_start_y) * pct)
                color = blue
                x_pos = start_x + (pkt.seqNum * 45)
            
            if self.selected_packet == pkt:
                color = green

            rect = pygame.Rect(x_pos, curr_y, box_w, 20)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, black, rect, 1)
            val = str(pkt.ackNum if pkt.isAck else pkt.seqNum)
            self.screen.blit(self.font.render(val, True, black), (x_pos+12, curr_y))
            
            self.clickable_packets.append((rect, pkt))

        # --- RIGHT SIDE: LOG ---
        panel_x = 750
        pygame.draw.rect(self.screen, lightGray, (panel_x, 0, screenWidth-panel_x, screenHeight))
        pygame.draw.line(self.screen, black, (panel_x, 0), (panel_x, screenHeight), 2)
        
        log_title = self.title_font.render("EVENT LOG", True, black)
        self.screen.blit(log_title, (panel_x + 80, 20))
        
        y_off = 60
        for text, color in self.logs:
            log_surf = self.font.render(text, True, color)
            self.screen.blit(log_surf, (panel_x + 10, y_off))
            y_off += 25

        # --- FOOTER ---
        self.draw_legend()
        
        # FPS display
        spd_txt = f"Speed: {self.sim_speed} FPS"
        spd_surf = self.font.render(spd_txt, True, black)
        self.screen.blit(spd_surf, (560, 645))
        
        for btn in self.sim_buttons:
            btn.draw(self.screen)

    def run(self):
        while True:
            events = pygame.event.get()
            
            # switch to text cursor if hovering input
            hover_input = False
            mouse_pos = pygame.mouse.get_pos()
            if self.state == 'MENU':
                for box in self.inputs:
                    if box.rect.collidepoint(mouse_pos):
                        hover_input = True
                        break
            
            if hover_input:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_IBEAM)
            else:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.state == 'MENU':
                    self.handle_menu_events(event)
                else:
                    self.handle_sim_events(event)

            if self.state == 'SIMULATION' and not self.paused:
                self.channel.tick()
                self.sender.tick_timer()
                
                if self.sender.base == self.sender.totalPackets:
                    print("\n--- SIMULATION DONE ---\n")
                    self.add_log("DONE!", green)
                    self.paused = True

            if self.state == 'MENU':
                self.draw_menu()
            else:
                self.draw_simulation()

            pygame.display.flip()
            self.clock.tick(self.sim_speed)

if __name__ == "__main__":
    vis = NetworkSim()
    vis.run()