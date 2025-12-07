"""
Name: Alyssa Pinnock
Course: EEL 4781 - Computer Communication Networks
Project: Programming Project - Option C (TCP-Like Protocol)
Description: Implements the Sender logic. It handles the sliding 
window, manages the retransmission timer, and detects when to fast 
retransmit.
"""

from packet import Packet

class Sender:
    def __init__(self, channel, windowSize, timeoutInterval, totalPackets, log_callback=None):
        self.channel = channel
        self.windowSize = windowSize      
        self.timeoutInterval = timeoutInterval
        self.totalPackets = totalPackets
        self.log = log_callback # helps print to the ui screen
        
        # tracking the window state
        self.base = 0              # oldest packet we haven't got an ack for yet
        self.nextSeqNum = 0        # next sequence number to be sent
        self.timerCount = 0        
        self.timerRunning = False  
        self.dupAckCount = 0       # counts duplicates for fast retransmit
        
        self.receiver_ref = None   

    def set_receiver_ref(self, receiver):
        self.receiver_ref = receiver

    def is_window_full(self):
        # helper so the UI knows if it should disable the send button.
        # we also need to stop if we hit the total packet limit.
        return (self.nextSeqNum >= self.base + self.windowSize) or \
               (self.nextSeqNum >= self.totalPackets)

    def attempt_send_one(self):
        # this is called when the user clicks "Send New".
        # first, check if we actually have space in the window
        if not self.is_window_full():
            
            pkt = Packet(seqNum=self.nextSeqNum, data=f"Msg{self.nextSeqNum}")
            
            if self.log: self.log(f"[Sender] Manually Sent {self.nextSeqNum}")
            print(f" [Sender] Sending Data {self.nextSeqNum}")
            
            # send it off to the channel
            self.channel.send_to_channel(pkt, self.receiver_ref)
            
            # if this is the first packet in the window, we need to start the timer
            if self.base == self.nextSeqNum:
                self.start_timer()
            
            self.nextSeqNum += 1
            return True # tell UI it worked
        else:
            return False # tell UI it failed (window full)

    def receive(self, packet):
        # ignore data packets, we only care about ACKs here
        if not packet.isAck: return

        print(f" [Sender] Received ACK {packet.ackNum}")

        # if the ack number is greater than our base, it's a "New ACK"
        # this means the receiver got new data, so we can slide the window.
        if packet.ackNum > self.base:
            self.base = packet.ackNum
            self.timerRunning = False
            self.dupAckCount = 0 # reset this since we made progress
            
            if self.log: self.log(f"[Sender] Got ACK {packet.ackNum}", (0, 100, 0))
            
            # restart timer if there are still packets left in the window
            if self.base < self.nextSeqNum:
                self.start_timer()
                
        # if the ack is the same as the base, it's a duplicate.
        # this usually means the receiver got a packet out of order.
        elif packet.ackNum == self.base:
            self.dupAckCount += 1
            if self.log: self.log(f"[Sender] Dup ACK {packet.ackNum} ({self.dupAckCount})", (200, 100, 0))
            
            # Fast Retransmit: if we get 3 duplicates (so 4 total), we assume loss
            # and resend immediately without waiting for timeout.
            if self.dupAckCount == 3: 
                msg = "!!! FAST RETRANSMIT !!!"
                print(msg)
                if self.log: self.log(msg, (255, 0, 0))
                self.retransmit()

    def tick_timer(self):
        # this runs every frame of the simulation
        if self.timerRunning:
            self.timerCount += 1
            # check if we passed the limit
            if self.timerCount >= self.timeoutInterval:
                msg = "!!! TIMEOUT !!!"
                print(msg)
                if self.log: self.log(msg, (255, 0, 0))
                self.retransmit()
                self.start_timer() # restart immediately after timeout

    def start_timer(self):
        self.timerCount = 0
        self.timerRunning = True

    def retransmit(self):
        # only retransmit the oldest packet (base) that hasn't been acked yet
        if self.base < self.totalPackets:
            if self.log: self.log(f"[Sender] Re-sending {self.base}", (255, 0, 0))
            pkt = Packet(seqNum=self.base, data=f"Msg{self.base}")
            self.channel.send_to_channel(pkt, self.receiver_ref)