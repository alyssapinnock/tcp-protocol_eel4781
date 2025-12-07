"""
Name: Alyssa Pinnock
Course: EEL 4781 - Computer Communication Networks
Project: Programming Project - Option C (TCP-Like Protocol)
Description: Receiver logic that handles accepting data in order, 
buffering out-of-order packets, and sending cumulative ACKs.
"""

from packet import Packet

class Receiver:
    def __init__(self, channel, log_callback=None):
        self.channel = channel
        self.expectedSeqNum = 0
        self.received_data = [] 
        # using a dictionary for the buffer to easily packets by their seq number
        self.buffer = {} 
        self.sender_ref = None
        self.log = log_callback # used to update the UI log

    def set_sender_ref(self, sender):
        self.sender_ref = sender

    def receive(self, packet):
        # receivers don't care about ACKs, so just ignore them
        if packet.isAck: return 

        # Case 1: we got exactly what we were expecting
        if packet.seqNum == self.expectedSeqNum:
            if self.log: self.log(f"[Recv] Accepted {packet.seqNum}", (0, 0, 255))
            print(f" [Receiver] Accepted Packet {packet.seqNum}")
            
            self.received_data.append(packet.data)
            self.expectedSeqNum += 1
            
            # check the buffer to see if we already have the next few packets.
            # if we do, we can deliver them to the app layer right now.
            while self.expectedSeqNum in self.buffer:
                if self.log: self.log(f"[Recv] Unbuffered {self.expectedSeqNum}", (0, 0, 255))
                self.received_data.append(self.buffer.pop(self.expectedSeqNum).data)
                self.expectedSeqNum += 1

        # Case 2: we got a packet from the future (out of order)
        elif packet.seqNum > self.expectedSeqNum:
            # only buffer it if we haven't seen it before
            if packet.seqNum not in self.buffer:
                if self.log: self.log(f"[Recv] Buffered {packet.seqNum} (Gap!)", (255, 165, 0))
                print(f" [Receiver] Buffered Packet {packet.seqNum}")
                self.buffer[packet.seqNum] = packet
            
        # Case 3: it's an old packet we already processed
        else:
            if self.log: self.log(f"[Recv] Ignored Dup {packet.seqNum}")

        # critical tcp feature: always send an ACK for the *next* packet we need.
        # this is how the sender knows if we have a gap or if we are up to date.
        ack_packet = Packet(seqNum=-1, isAck=True, ackNum=self.expectedSeqNum)
        
        if self.log: self.log(f"[Recv] Sent ACK {self.expectedSeqNum}", (200, 180, 0))
        print(f" [Receiver] Sending ACK {self.expectedSeqNum}")
        
        self.channel.send_to_channel(ack_packet, self.sender_ref)